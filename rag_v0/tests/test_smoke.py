import os, subprocess, pytest, time

@pytest.mark.asyncio
async def test_search_smoke():
    q = "test a simple retrieval path"
    t0=time.time()
    out = subprocess.check_output(["python3","rag_v0/scripts/10_search.py","--query",q,"--k","5"]).decode("utf-8")
    assert "rank" in out
    assert (time.time()-t0) < 10.0  # generous local smoke latency
