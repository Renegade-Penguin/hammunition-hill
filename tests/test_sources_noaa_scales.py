# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""NOAA's R/S/G scales: a hostile `Scale` value is a zero, not a crash.

The weekly 600 s fuzz run found `{"0": {"R": {"Scale": 1e999}}}`: Python's JSON
parser reads `1e999` as infinity, and `int(inf)` raises `OverflowError`, which
is neither of the two errors the parser caught.
"""

import httpx
import pytest

from hammunition_hill.config import SourceConfig
from hammunition_hill.sources.swpc_text import NoaaScalesSource


async def run(body):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=body, headers={"content-type": "application/json"})
    )
    cfg = SourceConfig(id="t", kind="noaa_scales", url="https://services.swpc.noaa.gov/scales.json")
    async with httpx.AsyncClient(transport=transport) as client:
        return await NoaaScalesSource().fetch(client, cfg)


async def test_a_normal_scale_is_read():
    data = await run('{"0": {"R": {"Scale": "0"}, "S": {"Scale": "1"}, "G": {"Scale": "3"}}}')

    assert data["scales"]["G"]["scale"] == 3
    assert data["worst"] == 3


@pytest.mark.parametrize("raw", ["1e999", "-1e999", '"nan"', '"x"', "[]", "null"])
async def test_an_unreadable_scale_reads_as_zero(raw):
    data = await run(f'{{"0": {{"R": {{"Scale": {raw}}}}}}}')

    assert data["scales"]["R"]["scale"] == 0
    assert data["scales"]["R"]["label"] == "R0"
