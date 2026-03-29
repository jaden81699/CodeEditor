import re
from typing import Optional

JAVA_PRIMITIVES = {
    "byte", "short", "int", "long", "float", "double", "boolean", "char", "void", "String"
}


def _normalize_java_type(t: str) -> str:
    """
    Normalize Java type strings for comparison.
    Examples:
      'int []' -> 'int[]'
      ' String ' -> 'String'
      'final int' -> 'int'
    """
    t = (t or "").strip()
    t = re.sub(r"\bfinal\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace(" []", "[]").replace("[ ]", "[]")
    return t


def _extract_class_name(source: str) -> Optional[str]:
    """
    Returns the declared class name if found.
    Supports 'public class X' and 'class X'.
    """
    m = re.search(r"\b(?:public\s+)?class\s+([A-Za-z_]\w*)\b", source)
    return m.group(1) if m else None


def _split_params(param_str: str) -> list[str]:
    """
    Splits a simple Java parameter list.
    Example:
      'int amount, String name' -> ['int', 'String']
    """
    param_str = (param_str or "").strip()
    if not param_str:
        return []

    params = []
    for raw in param_str.split(","):
        raw = raw.strip()
        # remove annotations if any
        raw = re.sub(r"@\w+\s*", "", raw)
        raw = re.sub(r"\bfinal\b", "", raw).strip()

        # naive split: everything except the last token is treated as the type
        # e.g. "int amount" -> "int"
        #      "String[] arr" -> "String[]"
        parts = raw.split()
        if len(parts) >= 2:
            ptype = " ".join(parts[:-1])
        else:
            # fallback if malformed
            ptype = raw

        params.append(_normalize_java_type(ptype))
    return params


def _extract_method_signatures(source: str, class_name: Optional[str] = None) -> list[dict]:
    """
    Very lightweight Java method parser.
    Returns a list like:
      [
        {
          "name": "makeChange",
          "return_type": "int",
          "params": ["int"]
        }
      ]

    This is intentionally simple and is good enough for starter-code contracts.
    """
    methods = []

    # Remove line comments and block comments to reduce noise
    src = re.sub(r"//.*", "", source)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)

    # Match typical Java method declarations
    pattern = re.compile(
        r"""
        (?:
            public|private|protected
        )?\s*
        (?:
            static\s+
        )?
        (?P<return_type>[A-Za-z_][\w<>,\s?]*(?:\[\])*)\s+
        (?P<name>[A-Za-z_]\w*)\s*
        \(
            (?P<params>[^)]*)
        \)\s*
        \{
        """,
        re.VERBOSE
    )

    for m in pattern.finditer(src):
        name = m.group("name")
        return_type = _normalize_java_type(m.group("return_type"))
        params = _split_params(m.group("params"))

        # Skip constructors
        if class_name and name == class_name:
            continue

        methods.append({
            "name": name,
            "return_type": return_type,
            "params": params,
        })

    return methods


def _format_method_sig(name: str, params: list[str], return_type: Optional[str] = None) -> str:
    param_str = ", ".join(params)
    if return_type:
        return f"{return_type} {name}({param_str})"
    return f"{name}({param_str})"


def _validate_submission_contract(question, user_code: str) -> Optional[str]:
    """
    Returns a friendly error string if the submitted code violates the expected
    class/method contract. Returns None if the contract looks valid.
    """
    starter = (question.user_starter_code or "").strip()

    # 1) expected class name
    expected_class = _extract_class_name(starter) or "Solution"
    user_class = _extract_class_name(user_code)

    if not user_class:
        return (
            f"Your code must define a class named '{expected_class}'. "
            f"No class declaration was found."
        )

    if user_class != expected_class:
        return (
            f"Expected class name: '{expected_class}'. "
            f"Found class name: '{user_class}'. "
            f"Please keep the required class name the same as the starter code."
        )

    # 2) expected method signature
    expected_methods = _extract_method_signatures(starter, class_name=expected_class)

    if not expected_methods:
        # If starter code has no obvious method signature, skip validation
        return None

    # Usually starter code should define the one required method.
    expected = expected_methods[0]

    user_methods = _extract_method_signatures(user_code, class_name=user_class)

    exact_name_matches = [m for m in user_methods if m["name"] == expected["name"]]

    if not exact_name_matches:
        found_names = sorted({m["name"] for m in user_methods})
        found_text = ", ".join(found_names) if found_names else "no methods found"
        return (
            f"Expected method '{_format_method_sig(expected['name'], expected['params'], expected['return_type'])}' "
            f"was not found.\n\n"
            f"Please do not rename the required method from the starter code.\n"
            f"Methods found in your submission: {found_text}"
        )

    # 3) parameter count/types
    matching_param_count = [m for m in exact_name_matches if len(m["params"]) == len(expected["params"])]
    if not matching_param_count:
        found_sigs = ", ".join(
            _format_method_sig(m["name"], m["params"], m["return_type"]) for m in exact_name_matches
        )
        return (
            f"The method '{expected['name']}' exists, but its parameter count does not match.\n\n"
            f"Expected: {_format_method_sig(expected['name'], expected['params'], expected['return_type'])}\n"
            f"Found: {found_sigs}"
        )

    exact_param_match = None
    for m in matching_param_count:
        if m["params"] == expected["params"]:
            exact_param_match = m
            break

    if exact_param_match is None:
        found_sigs = ", ".join(
            _format_method_sig(m["name"], m["params"], m["return_type"]) for m in matching_param_count
        )
        return (
            f"The method '{expected['name']}' exists, but its parameter types do not match.\n\n"
            f"Expected: {_format_method_sig(expected['name'], expected['params'], expected['return_type'])}\n"
            f"Found: {found_sigs}"
        )

    # 4) return type
    if exact_param_match["return_type"] != expected["return_type"]:
        return (
            f"The return type for '{expected['name']}' does not match the required signature.\n\n"
            f"Expected: {_format_method_sig(expected['name'], expected['params'], expected['return_type'])}\n"
            f"Found: {_format_method_sig(exact_param_match['name'], exact_param_match['params'], exact_param_match['return_type'])}"
        )

    return None
