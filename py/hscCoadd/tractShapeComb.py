#!/usr/bin/env python
# encoding: utf-8
"""Combine the Shape mask for an entire Tract."""

import argparse
import coaddPatchNoData as cdNoData


def run(rootDir, tractUse, filter, prefix):
    """Run tractShape."""
    cdNoData.tractShape(rootDir, tractUse, filter=filter, prefix=prefix,
                        notRun=False, saveList=True, combine=True,
                        showPatch=True, checkCat=True)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Root directory of data")
    parser.add_argument("tract", type=int, help="Tract Number")
    parser.add_argument("-f", dest='filter', help="HSC Filter",
                        default='HSC-I')
    parser.add_argument("-p", dest='prefix', help="Prefix for the output",
                        default='ssp385_wide')

    args = parser.parse_args()

    run(args.root, args.tract, filter=args.filter, prefix=args.prefix)
