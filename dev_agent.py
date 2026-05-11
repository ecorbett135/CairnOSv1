import argparse
from dev_agent.agent import DevAgent

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode")

    feature_parser = subparsers.add_parser("feature")
    feature_parser.add_argument("request", type=str)

    args = parser.parse_args()

    agent = DevAgent()

    if args.mode == "feature":
        agent.run_feature(args.request)
    else:
        agent.run_repair()

if __name__ == "__main__":
    main()
