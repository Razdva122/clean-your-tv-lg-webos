"""Frozen GUI entry point with an offline packaging check."""
import sys

if __name__ == '__main__':
    if '--check-runtime' in sys.argv and getattr(sys, 'frozen', False):
        import subprocess
        from cytv.runtime_check import check_ffmpeg_runtime
        try:
            check_ffmpeg_runtime()
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            if sys.stderr:
                print('Desktop runtime verification failed: ' + str(error), file=sys.stderr)
            raise SystemExit(1)
    if any(flag in sys.argv for flag in ('--check-payload', '--check-runtime', '--version')):
        from cytv.cli import main
        from cytv.terminal import Console, supports_ansi
        raise SystemExit(main(write=Console(lambda text: print(text) if sys.stdout else None,
                                          interactive=supports_ansi())))
    from cytv.gui import main
    raise SystemExit(main())
