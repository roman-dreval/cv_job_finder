from job_finder import hardware

GIB = 2 ** 30


def test_model_for_vram():
    assert hardware.model_for_vram(12.0) == "google/gemma-4-12b"
    assert hardware.model_for_vram(9.9) == "google/gemma-4-12b"  # a 10 GB card reports a bit less
    assert hardware.model_for_vram(7.9) == "google/gemma-4-e4b"  # 8 GB: the 12B with its context doesn't fit
    assert hardware.model_for_vram(None) == "google/gemma-4-12b"  # unknown: the usual model


def test_vram_from_registry_values():
    # REG_BINARY bytes or a REG_QWORD number; the biggest card counts
    assert hardware.vram_gb(lambda: [(12 * GIB).to_bytes(8, "little"), 128 * 2 ** 20]) == 12.0
    assert hardware.vram_gb(lambda: []) is None
    assert hardware.vram_gb(lambda: [b"", "junk", 0]) is None

    def no_access():
        raise OSError("access denied")

    assert hardware.vram_gb(no_access) is None
