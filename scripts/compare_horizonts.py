"""Test"""
#pylint: disable=import-error, wrong-import-position
import os
import sys
import argparse
import json
import logging

import numpy as np
from tqdm import tqdm
from glob import glob

sys.path.append('..')
from seismiqb import read_point_cloud, make_labels_dict



def compare(horizont_1, horizont_2):
    """ Compare two horizonts by computing multiple simple metrics.
    
    Parameters
    ----------
    horizont_1, horizont_2 : str
        Path to horizont. Each line in the file must be in (iline, xline, height) format.
        
    Returns
    -------
    dict
        Computed metrics.
    """
    point_cloud_1 = read_point_cloud(horizont_1)
    labels_1 = make_labels_dict(point_cloud_1)

    point_cloud_2 = read_point_cloud(horizont_2)
    labels_2 = make_labels_dict(point_cloud_2)

    differences = []
    not_present_1, not_present_2 = 0, 0
    vals_1, vals_2 = [], []

    for key, val_1 in labels_1.items():
        if labels_2.get(key) is not None:
            val_2 = labels_2.get(key)
            diff = abs(val_2[0] - val_1[0])
            differences.append(diff)

            vals_1.append(val_1)
            vals_2.append(val_2)
        else:
            not_present_1 += 1

    for key, val_2 in labels_2.items():
        if labels_1.get(key) is None:
            not_present_2 += 1

    info = {'name_1': '/'.join(horizont_1.split('/')[-3:]),
            'name_2': '/'.join(horizont_2.split('/')[-3:]),
            'mean_error': np.mean(differences),
            'std_error':  np.std(differences),
            'len_1': len(labels_1),
            'len_2': len(labels_2),
            'in_window':  sum(np.array(differences) <= 5),
            'rate_in_window': sum(np.array(differences) <= 5) / len(differences),
            'mean_1': np.mean(vals_1),
            'mean_2': np.mean(vals_2),
            'not_present_1': not_present_1,
            'not_present_2': not_present_2,
            }
    return info


def main(dir_1, dir_2, printer=None):
    """ Compare each pair of horizonts in passed lists.
    
    Parameters
    ----------
    dir_1, dir_2 : str
        Path to directories with horizonts to compare.
        
    printer : callable
        Function to print with.
    """
    list_1 = glob(dir_1)
    list_2 = glob(dir_2)
    cross = [(item_1, item_2) for item_1 in list_1 for item_2 in list_2]

    for horizont_1, horizont_2 in tqdm(cross):
        info = compare(horizont_1, horizont_2)

        printer('First horizont:  {}'.format(info['name_1']))
        printer('Second horizont: {}'.format(info['name_2']))

        printer('Mean value/std of error:                  {:8.7} / {:8.7}'.format(info['mean_error'], info['std_error']))
        printer('First horizont length:                    {}'.format(info['len_1']))
        printer('Second horizont length:                   {}'.format(info['len_2']))

        printer('Number in 5 ms window:                    {}'.format(info['in_window']))
        printer('Rate in 5 ms window:                      {:8.7}'.format(info['rate_in_window']))

        printer('Average height of FIRST horizont:         {:8.7}'.format(info['mean_1']))
        printer('Average height of SECOND horizont:        {:8.7}'.format(info['mean_2']))

        printer('In the FIRST, but not in the SECOND:      {}'.format(info['not_present_1']))
        printer('In the SECOND, but not in the FIRST:      {}'.format(info['not_present_2']))
        printer('\n\n')


if __name__ == '__main__':
    # Get arguments from passed json
    parser = argparse.ArgumentParser(description="Compare two lists of horizonts.")
    parser.add_argument("--config_path", type=str, default="./config_compare.json")
    args = parser.parse_args()

    with open(args.config_path, 'r') as file:
        config = json.load(file)
        args = [config.get(key) for key in ["dir_1", "dir_2"]]
        
    # Logging to either stdout or file
    if config.get("print"):
        printer = print
    else:
        path_log = config.get("path_log") or os.path.join(os.getcwd(), "compare.log")
        handler = logging.FileHandler(path_log, mode='w')        
        handler.setFormatter(logging.Formatter('%(message)s'))

        logger = logging.getLogger('compare_logger')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        printer = logger.info
    
    # Compare each pair of horizonts in two directories
    main(*args, printer=printer)
