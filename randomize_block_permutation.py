import random
from django.db import transaction
from django.utils import timezone
from editor.models import ParticipantProfile, RandomizationBlock, EnrollmentCap

# Randomize block size to reduce predictability
BLOCK_SIZES = (4, 6, 8)


def _build_feasible_block(need_c: int, need_e: int, size: int) -> list[str]:
    """
    Build a block up to `size` labels without exceeding remaining capacity.
    Prefer balance (half/half) when possible; fill remainder from the arm that still has room.
    """
    need_c = max(int(need_c), 0)
    need_e = max(int(need_e), 0)
    size = max(int(size), 1)

    total_remaining = need_c + need_e
    if total_remaining <= 0:
        return []

    # Don't build a block bigger than remaining enrollment
    size = min(size, total_remaining)

    half = size // 2
    c = min(half, need_c)
    e = min(half, need_e)

    labels = ["C"] * c + ["E"] * e

    # Fill leftover slots (if size is odd or one arm has more capacity)
    remaining_slots = size - len(labels)
    rem_c = need_c - c
    rem_e = need_e - e

    while remaining_slots > 0 and (rem_c > 0 or rem_e > 0):
        # Fill from the arm with more remaining capacity (ties go to C)
        if rem_c >= rem_e and rem_c > 0:
            labels.append("C")
            rem_c -= 1
        elif rem_e > 0:
            labels.append("E")
            rem_e -= 1
        remaining_slots -= 1

    random.shuffle(labels)
    return labels


@transaction.atomic
def assign_group(user) -> str:
    """
    Permuted-block randomization with caps.
    Uses DB row locks on:
      - participant profile (avoid double-assign)
      - the single cap row (serialize assignments)
      - the single randomization block row (serialize sequence)
    """
    # Lock the participant row
    profile, _ = (
        ParticipantProfile.objects
        .select_for_update()
        .get_or_create(user=user)
    )

    if profile.group in ("C", "E"):
        return profile.group

    # Lock a single cap row (use PK=1 so you never accidentally have multiple cap rows)
    cap, _ = (
        EnrollmentCap.objects
        .select_for_update()
        .get_or_create(pk=1)
    )

    # Current totals (computed while holding the cap lock, so assignments serialize)
    nC = ParticipantProfile.objects.filter(group="C").count()
    nE = ParticipantProfile.objects.filter(group="E").count()
    need_c = max(cap.target_C - nC, 0)
    need_e = max(cap.target_E - nE, 0)

    if need_c == 0 and need_e == 0:
        raise RuntimeError("Enrollment full (both arms at cap).")

    # Lock the single global sequence row
    rb, _ = (
        RandomizationBlock.objects
        .select_for_update()
        .get_or_create(pk=1)
    )

    # Normalize None -> []
    if rb.sequence is None:
        rb.sequence = []

    # If we ran out of labels, build a new feasible block
    if not rb.sequence:
        size = rb.block_size or random.choice(BLOCK_SIZES)
        rb.sequence = _build_feasible_block(need_c, need_e, size)

        # If still empty (should only happen if total_remaining == 0)
        if not rb.sequence:
            arm = "C" if need_c > 0 else "E"
            profile.group = arm
            profile.randomized_at = timezone.now()
            profile.save(update_fields=["group", "randomized_at"])
            return arm

    # Deal a label that still has capacity (skip labels that no longer fit near caps)
    arm = None
    while rb.sequence:
        candidate = rb.sequence.pop()
        if candidate == "C" and need_c > 0:
            arm = "C"
            break
        if candidate == "E" and need_e > 0:
            arm = "E"
            break

    # If the remaining sequence can't satisfy capacity, force the only possible arm
    if arm is None:
        if need_c > 0:
            arm = "C"
        elif need_e > 0:
            arm = "E"
        else:
            raise RuntimeError("No capacity left.")

    rb.save(update_fields=["sequence"])

    profile.group = arm
    profile.randomized_at = timezone.now()
    profile.save(update_fields=["group", "randomized_at"])
    return arm
