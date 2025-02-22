"""Tests for podman client"""

import pytest
import re
from repo2podman.podman import PodmanCommandError, PodmanContainer, PodmanEngine
from time import sleep


BUSYBOX = "docker.io/library/busybox"


def test_run():
    client = PodmanEngine(parent=None)
    c = client.run(BUSYBOX, command=["id", "-un"])
    assert isinstance(c, PodmanContainer)

    # If image was pulled the progress logs will also be present
    out = c.logs().splitlines()
    assert out[-1].strip() == b"root", out

    out = c.logs(timestamps=True).splitlines()
    timestamp, msg = out[-1].strip().split(b" ", 1)
    assert re.match(br"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\S+", timestamp)
    assert msg == b"root", out

    c.remove()
    with pytest.raises(PodmanCommandError) as exc:
        c.reload()
    assert "".join(exc.value.output).strip() == "[]"


def test_run_autoremove():
    client = PodmanEngine(parent=None)
    # Need to sleep in container to prevent race condition
    c = client.run(BUSYBOX, command=["sh", "-c", "sleep 1; id -un"], remove=True)
    # Sleep to ensure container has exited
    sleep(2)
    with pytest.raises(PodmanCommandError) as exc:
        c.reload()
    assert "".join(exc.value.output).strip() == "[]"


def test_run_detach_wait():
    client = PodmanEngine(parent=None)
    c = client.run(BUSYBOX, command=["sh", "-c", "echo before; sleep 5; echo after"])
    assert re.match("^[0-9a-f]{64}$", c.id)
    # If image was pulled the progress logs will also be present
    out = c.logs().splitlines()
    assert out[-1].strip() == b"before", out
    c.wait()
    out = c.logs().splitlines()
    assert out[-1].strip() == b"after", out
    c.remove()
    with pytest.raises(PodmanCommandError) as exc:
        c.reload()
    assert "".join(exc.value.output).strip() == "[]"


def test_run_detach_nostream():
    client = PodmanEngine(parent=None)
    c = client.run(BUSYBOX, command=["id", "-un"])
    assert re.match("^[0-9a-f]{64}$", c.id)
    sleep(1)
    c.reload()
    assert c.status == "exited"
    out = c.logs()
    assert out.strip() == b"root"
    c.remove()
    with pytest.raises(PodmanCommandError):
        c.reload()


def test_run_detach_stream_live():
    client = PodmanEngine(parent=None)
    c = client.run(BUSYBOX, command=["sh", "-c", "sleep 5; id -un"])
    assert isinstance(c, PodmanContainer)
    assert re.match("^[0-9a-f]{64}$", c.id)
    sleep(1)
    c.reload()
    assert c.status == "running"
    out = "\n".join(line.decode("utf-8") for line in c.logs(stream=True))
    assert "".join(out).strip() == "root"
    c.remove()
    with pytest.raises(PodmanCommandError):
        c.reload()


def test_run_detach_stream_exited():
    client = PodmanEngine(parent=None)
    c = client.run(BUSYBOX, command=["id", "-un"])
    assert isinstance(c, PodmanContainer)
    assert re.match("^[0-9a-f]{64}$", c.id)
    sleep(1)
    c.reload()
    assert c.status == "exited"
    out = "\n".join(line.decode("utf-8") for line in c.logs(stream=True))
    assert "".join(out).strip() == "root"
    c.remove()
    with pytest.raises(PodmanCommandError):
        c.reload()
