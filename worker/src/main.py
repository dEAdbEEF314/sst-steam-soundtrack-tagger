import argparse

from pipeline import sst_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SST Worker Pipeline")
    parser.add_argument("--app-id", type=int, required=True)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("files", nargs="+", help="Target audio files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = sst_pipeline(
        app_id=args.app_id,
        files=args.files,
        config_path=args.config,
        dry_run=args.dry_run,
    )
    print(result)


if __name__ == "__main__":
    main()
