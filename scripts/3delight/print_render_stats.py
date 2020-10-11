#!/usr/bin/python
from __future__ import print_function
import json, sys, os

# Given on stdin then output of 3delight's "i-disply -metadata filename.exr",
# this scripts parses it and returns normalized render costs in minutes.
# This approximites how 3delight cloud compute render costs.


def get_normalized_render_cost(json):
    """"""
    profiling = json['profiling']
    threads = json['system']['started_threads']
    cpu_usage = sum(profiling['cpu_usage'])
    cpu_idle  = sum(profiling['cpu_idle'])
    assert(not None in [cpu_usage, cpu_idle, threads])
    cpu_time = (cpu_usage+cpu_idle)/threads
    return cpu_time


def main():

    json_input = sys.stdin.read()
    json_object = {}

    if len(json_input) == 0:
        print("Provide to stdin an input as printed from i-display -metadata file.exr")
        return 1

    try:
        json_object = json.loads(json_input)
    except:
        print("Can't parse input: \n\t{}".format(json_input))
        return 1

    minutes = get_normalized_render_cost(json_object)
    print(minutes/60)

if __name__ == '__main__': main()
        