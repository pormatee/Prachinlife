def _major(version):
    try:
        return int(str(version).split(".")[0])
    except (ValueError, TypeError):
        return None


def check_compatibility(
    runtime_version,
    semantic_contract_version,
    state_schema_version,
    domain_pack_version,
):
    if _major(runtime_version) != 1:
        return False, "INCOMPATIBLE_CONTRACT"

    if _major(semantic_contract_version) != 1:
        return False, "INCOMPATIBLE_CONTRACT"

    if state_schema_version != 1:
        return False, "INCOMPATIBLE_CONTRACT"

    if _major(domain_pack_version) != 1:
        return False, "INCOMPATIBLE_CONTRACT"

    return True, "OK"
