"""Coder usernames must round-trip to Computor user ids.

Coder needs a username, Computor has UUIDs, and Coder caps names at 32
characters — so the old scheme (``"u" + str(uuid)``, truncated) lost the last
five characters of every id. That forced prefix matching on every consumer and,
worse, let the workspace app secret be derived from a *different* string than
the one provisioning derived it from.

Base32 of the UUID's bytes fits in 27 characters and is reversible, which is
what these tests pin: encode/decode is exact, and matching is equality.
"""

import uuid

import pytest

from computor_backend.coder.naming import (
    coder_username_matches_user,
    decode_coder_username,
    encode_coder_username,
)

UID = "0232de59-e05d-4bc2-898f-b879c06abcde"
OTHER_UID = "0232de59-e05d-4bc2-898f-b879c06abcdf"  # differs only in the LAST char


@pytest.mark.parametrize(
    "raw",
    [
        UID,
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
        UID.upper(),
        str(uuid.uuid5(uuid.NAMESPACE_DNS, "computor")),
    ],
)
def test_encode_decode_round_trips(raw):
    name = encode_coder_username(raw)
    assert decode_coder_username(name) == str(uuid.UUID(raw))


def test_encoded_name_satisfies_coders_rules():
    name = encode_coder_username(UID)
    assert len(name) == 27, name          # comfortably inside Coder's 32
    assert name[0] == "u"                 # must start with a letter
    assert name.isalnum() and name.islower()


def test_ids_differing_only_in_the_last_character_encode_differently():
    # The exact case the old truncating scheme collapsed: 36-char ids sharing
    # their first 31 characters produced one and the same Coder username.
    assert encode_coder_username(UID) != encode_coder_username(OTHER_UID)


@pytest.mark.parametrize(
    "name",
    [
        None,
        "",
        "admin",                                  # Coder's own account
        "u" + UID,                                # untruncated legacy form
        ("u" + UID)[:32],                         # the old truncated form
        "u" + "1" * 26,                           # right length, outside the base32 alphabet
        "u" + "0189" + "a" * 22,                  # ditto, mixed in
        encode_coder_username(UID)[:-1],          # wrong length
        "x" + encode_coder_username(UID)[1:],     # wrong prefix
    ],
)
def test_decode_rejects_anything_we_did_not_encode(name):
    assert decode_coder_username(name) is None


def test_match_accepts_the_encoded_name_and_the_bare_id():
    # Internal callers and tests address workspaces by the bare user id.
    assert coder_username_matches_user(encode_coder_username(UID), UID)
    assert coder_username_matches_user(UID, UID)


def test_match_rejects_another_users_name():
    assert not coder_username_matches_user(encode_coder_username(OTHER_UID), UID)
    assert not coder_username_matches_user("admin", UID)
    assert not coder_username_matches_user(None, UID)


def test_match_is_not_a_prefix_rule():
    # A short prefix of a valid name must never authorize the whole id; under
    # the old startswith() comparison "u0232de59" authorized this user.
    assert not coder_username_matches_user("u0232de59", UID)


def test_any_well_formed_name_decodes_to_some_uuid():
    """Decoding validates the ENCODING, not the existence of the user.

    Every 27-character name over the base32 alphabet maps to a valid UUID, so
    decode alone is not an authorization check — callers must still resolve the
    id against the database (``_computor_user_for_coder_name``) or compare it to
    an authenticated principal (``coder_username_matches_user``).
    """
    fabricated = "u" + "a" * 26
    assert decode_coder_username(fabricated) is not None
    assert not coder_username_matches_user(fabricated, UID)


def test_non_uuid_ids_still_produce_a_name_coder_accepts():
    # Fixtures and service ids are not UUIDs; they are not addressable, but
    # they must not blow up or emit something Coder would reject.
    name = encode_coder_username("s1")
    assert name == "us1"
    assert decode_coder_username(name) is None
