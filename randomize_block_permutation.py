import random
from django.db import transaction
from django.utils import timezone
from editor.models import ParticipantProfile, RandomizationBlock, EnrollmentCap

BLOCK_SIZES = [4, 6, 8]  # randomize block size to reduce predictability


def _build_feasible_block(need_c: int, need_e: int, size: int) -> list[str]:
    """
    Make a balanced block that won't exceed remaining capacity.
    If one arm is almost full, we shrink to what's feasible.
    """
    half = size // 2
    take_c = min(half, need_c)
    take_e = min(half, need_e)

    # If both have some room, keep it balanced
    m = min(take_c, take_e)
    if m > 0:
        labels = ['C'] * m + ['E'] * m
        random.shuffle(labels)
        return labels

    # If one arm is full, only emit the other (at most half, still shuffled trivially)
    if need_c > 0 and need_e == 0:
        return ['C'] * min(half, need_c)
    if need_e > 0 and need_c == 0:
        return ['E'] * min(half, need_e)

    return []  # truly no capacity


@transaction.atomic
def assign_group(user) -> str:
    """
    Permuted-block randomization with hard caps.
    Transactional so concurrent signups remain balanced.
    """
    # Lock the participant row
    profile, _ = (ParticipantProfile.objects
                  .select_for_update()
                  .get_or_create(user=user))

    if profile.group in ('C', 'E'):
        return profile.group  # already assigned

    # Lock caps
    cap = (EnrollmentCap.objects
           .select_for_update()
           .first() or EnrollmentCap.objects.create())

    # Current totals
    nC = ParticipantProfile.objects.filter(group='C').count()
    nE = ParticipantProfile.objects.filter(group='E').count()
    need_c = max(cap.target_C - nC, 0)
    need_e = max(cap.target_E - nE, 0)

    if need_c == 0 and need_e == 0:
        raise RuntimeError("Enrollment full (both arms at cap).")

    # Lock the single global block row
    rb, _ = RandomizationBlock.objects.select_for_update().get_or_create(id=1)

    # If we ran out of labels, build a new feasible block
    if not rb.sequence:
        size = rb.block_size or random.choice(BLOCK_SIZES)
        # Randomize the size a bit to reduce predictability
        size = random.choice(BLOCK_SIZES)
        rb.sequence = _build_feasible_block(need_c, need_e, size)
        if not rb.sequence:
            # Fallback: if only one arm has capacity, assign that arm
            arm = 'C' if need_c > 0 else 'E'
            profile.group = arm
            profile.randomized_at = timezone.now()
            profile.save(update_fields=["group", "randomized_at"])
            return arm

    # Deal one label
    arm = rb.sequence.pop()

    # If that arm is out of capacity (can happen near the end), flip if possible
    if (arm == 'C' and need_c == 0) and (need_e > 0):
        arm = 'E'
    elif (arm == 'E' and need_e == 0) and (need_c > 0):
        arm = 'C'
    elif (arm == 'C' and need_c == 0) and (need_e == 0):
        raise RuntimeError("No capacity left.")
    elif (arm == 'E' and need_e == 0) and (need_c == 0):
        raise RuntimeError("No capacity left.")

    rb.save(update_fields=["sequence"])

    profile.group = arm
    profile.randomized_at = timezone.now()
    profile.save(update_fields=["group", "randomized_at"])
    return arm
