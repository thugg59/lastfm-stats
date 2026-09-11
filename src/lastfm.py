import hashlib


def sign_request(params: dict, secret: str) -> str:
    signable = {k: v for k, v in params.items() if k not in ("api_sig", "format")}
    ordered = sorted(signable.items())
    sig_string = "".join(f"{k}{v}" for k, v in ordered) + secret
    return hashlib.md5(sig_string.encode("utf-8")).hexdigest()