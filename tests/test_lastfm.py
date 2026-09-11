import hashlib
from src.lastfm import sign_request


def test_sign_request_matches_manual_md5():
    params = {"method": "auth.getSession", "api_key": "abc", "token": "xyz"}
    secret = "secret123"

    expected = hashlib.md5(
        "api_keyabcmethodauth.getSessiontokenxyzsecret123".encode("utf-8")
    ).hexdigest()

    assert sign_request(params, secret) == expected


def test_sign_request_is_order_independent():
    secret = "secret123"
    params_a = {"method": "auth.getSession", "api_key": "abc", "token": "xyz"}
    params_b = {"token": "xyz", "api_key": "abc", "method": "auth.getSession"}

    assert sign_request(params_a, secret) == sign_request(params_b, secret)


def test_sign_request_changes_with_different_secret():
    params = {"method": "auth.getSession", "api_key": "abc"}

    sig1 = sign_request(params, "secret1")
    sig2 = sign_request(params, "secret2")

    assert sig1 != sig2