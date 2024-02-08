from datasets import load_dataset
import argparse
import json
from pathlib import Path
import pyarrow.parquet as pq
import logging
import os
import random


def setup_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='reformatted')
    parser.add_argument('--data', type=str, default='HuggingFaceH4/ultrachat_200k')
    return parser.parse_args()


def load_and_process_data_ultrachat(dataset_name, split):
    try:
        dataset = load_dataset(dataset_name, split=split)
        reformatted_data = [{
            'rejected': [message['messages'][0], {"role": "assistant", "content": ""}], 
            'chosen': [message['messages'][0], message['messages'][1]]
        } for message in dataset]
        return reformatted_data
    except Exception as e:
        logging.error(f"Error loading or processing dataset: {e}")
        return []


def load_and_process_data_metamath(dataset_name, split):
    try:
        dataset = load_dataset(dataset_name, split=split)
        reformatted_data = [{
            'rejected': [{"role": "user", "content": message['query']}, {"role": "assistant", "content": ""}], 
            'chosen': [{"role": "user", "content": message['query']}, {"role": "assistant", "content": message['response']}]
        } for message in dataset]
        return reformatted_data
    except Exception as e:
        logging.error(f"Error loading or processing dataset: {e}")
        return []

def save_to_json(data, path):
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        logging.error(f"Error saving data to {path}: {e}")

def save_to_parquet(dataset, path):
    try:
        pq.write_table(dataset.data.table, path)
    except Exception as e:
        logging.error(f"Error saving data to {path}: {e}")

def main():
    args = setup_arg_parser()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.data == 'HuggingFaceH4/ultrachat_200k':
        train_data = load_and_process_data_ultrachat(args.data, 'train_sft')
        test_data = load_and_process_data_ultrachat(args.data, 'test_sft')
    elif args.data == 'meta-math/MetaMathQA':
        train_data = load_and_process_data_metamath(args.data, 'train')
        random.shuffle(train_data)
        train_data = train_data[:-1000]
        test_data = train_data[-1000:]

    train_json_path = output_dir / 'train.json'
    test_json_path = output_dir / 'test.json'

    save_to_json(train_data, train_json_path)
    save_to_json(test_data, test_json_path)

    dataset = load_dataset('json', data_files=str(train_json_path), split='train')
    dataset_test = load_dataset('json', data_files=str(test_json_path), split='train')

    save_to_parquet(dataset, output_dir / 'train_prefs-00000-of-00001.parquet')
    save_to_parquet(dataset_test, output_dir / 'test_prefs-00000-of-00001.parquet')

    os.remove(train_json_path)
    os.remove(test_json_path)

if __name__ == "__main__":
    main()