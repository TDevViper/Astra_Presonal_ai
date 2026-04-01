import os
import sys


def main() -> int:
    """
    Downloads/caches faster-whisper models into the repo so runtime can be offline.
    Safe to run multiple times.
    """
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        print(f"[prefetch_whisper] faster_whisper import failed: {e}")
        return 1

    model = os.environ.get("WHISPER_MODEL", "small")
    compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
    download_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "models", "whisper")
    )
    os.makedirs(download_root, exist_ok=True)

    print(f"[prefetch_whisper] model={model} compute_type={compute_type}")
    print(f"[prefetch_whisper] download_root={download_root}")
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if http_proxy or https_proxy:
        print(
            "[prefetch_whisper] proxy detected (will be used by underlying download libs)"
        )
        print(f"[prefetch_whisper] HTTP_PROXY set:  {bool(http_proxy)}")
        print(f"[prefetch_whisper] HTTPS_PROXY set: {bool(https_proxy)}")
    else:
        print("[prefetch_whisper] no HTTP(S)_PROXY env detected")

    try:
        # local_files_only=False intentionally: this command is for prefetching.
        WhisperModel(
            model,
            device="cpu",
            compute_type=compute_type,
            download_root=download_root,
            local_files_only=False,
        )
    except Exception as e:
        msg = str(e)
        print(f"[prefetch_whisper] download/cache failed: {msg}")
        if "403" in msg or "Forbidden" in msg:
            print(
                "[prefetch_whisper] hint: this usually means your proxy/firewall blocks HuggingFace downloads."
            )
            print(
                "[prefetch_whisper] hint: allowlist domains: huggingface.co, cdn-lfs.huggingface.co"
            )
            print(
                "[prefetch_whisper] hint: once downloaded, /realtime/status can run fully offline."
            )
        return 2

    print("[prefetch_whisper] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
