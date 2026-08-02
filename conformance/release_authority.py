"""Reviewed immutable release identities accepted by the G0 gate."""

from __future__ import annotations


DATA_V1_0_0 = {
    "name": "plenora-data-tools",
    "repository": "PlenoraETL/plenora-data-tools",
    "tag": "v1.0.0",
    "tag_object": "b4a5bcd827c1c815460029681e3ce25bff915c2c",
    "revision": "7a47504482569636b6c0e268477d155010d3b030",
    "release": {
        "id": 363535950,
        "url": "https://github.com/PlenoraETL/plenora-data-tools/releases/tag/v1.0.0",
        "draft": False,
        "prerelease": False,
    },
    "source_archive": {
        "sha256": "471a80438832fc62564b14675cf0a7581bd3e4df96ace1cf7374ac4be7b8d545",
        "bytes": 1403268,
    },
    "crates_publish": False,
}

DATA_V1_0_1 = {
    **DATA_V1_0_0,
    "tag": "v1.0.1",
    "tag_object": "c47a82f5b63a2c5cdf264057e5dbcc1a69a58d62",
    "revision": "aab8152902a209955b2ea657dfeaeea10408f866",
    "release": {
        "id": 363567976,
        "url": "https://github.com/PlenoraETL/plenora-data-tools/releases/tag/v1.0.1",
        "draft": False,
        "prerelease": False,
    },
    "source_archive": {
        "sha256": "c9474bfc9aaceb5ac4fe7598755adfe5b09ef83f7defb06d5ba24edcb9dcee69",
        "bytes": 1405535,
    },
}

IO_V1_0_0 = {
    "name": "plenora-IO-tools",
    "repository": "PlenoraETL/plenora-IO-tools",
    "tag": "v1.0.0",
    "tag_object": "679d023a311bb5b42c7dc7f8663e6d766c0b9973",
    "revision": "ca7f34c6b732700fa79f579f7b003df27ce54b09",
    "release": {
        "id": 363535956,
        "url": "https://github.com/PlenoraETL/plenora-IO-tools/releases/tag/v1.0.0",
        "draft": False,
        "prerelease": False,
    },
    "source_archive": {
        "sha256": "97a75cb3d09e16efd8b9d8eed3f8c2ec73983336d90ed94c9379821d382f033d",
        "bytes": 766222,
    },
    "crates_publish": False,
}

DATABASE_V1_0_0 = {
    "name": "plenora-database-tools",
    "repository": "PlenoraETL/plenora-database-tools",
    "tag": "v1.0.0",
    "tag_object": "b0b83ddc0fcabcb47b98eb361e35a0587965af94",
    "revision": "89c82c4c700550decc394bb1e43b22c8a32e44e1",
    "release": {
        "id": 363535961,
        "url": "https://github.com/PlenoraETL/plenora-database-tools/releases/tag/v1.0.0",
        "draft": False,
        "prerelease": False,
    },
    "source_archive": {
        "sha256": "52462c6cd0acd5338c432c6deccfc02664a1486dc7e6fc39394cd3f7df305a62",
        "bytes": 579822,
    },
    "crates_publish": False,
}

TRUSTED_INVENTORIES = {
    "plenora-system-v1.0.0": {
        record["name"]: record
        for record in (DATA_V1_0_0, IO_V1_0_0, DATABASE_V1_0_0)
    },
    "plenora-system-v1.0.1": {
        record["name"]: record
        for record in (DATA_V1_0_1, IO_V1_0_0, DATABASE_V1_0_0)
    },
}
