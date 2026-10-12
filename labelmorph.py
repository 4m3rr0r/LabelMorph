#!/usr/bin/env python3
"""LabelMorph: offline DNS label mutation and permutation generator."""
import argparse
import itertools
import re


def read_lines(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            item = line.strip().lower().rstrip('.')
            if item and not item.startswith('#'):
                yield item


def numeric_variants(label, start, end):
    matches = list(re.finditer(r'\d+', label))
    for match in matches:
        original = match.group()
        # Prioritize adjacent values for each numeric segment before the full range.
        # Example: stage2p2488 -> stage3p2488 AND stage2p2489.
        near = [int(original) + 1, int(original) - 1]
        values = itertools.chain((n for n in near if start <= n <= end), range(start, end + 1))
        for n in dict.fromkeys(values):
            replacement = str(n).zfill(len(original)) if original.startswith('0') else str(n)
            yield label[:match.start()] + replacement + label[match.end():]


def variants(labels, words, start, end, numbers, keywords):
    yield tuple(labels)
    if numbers:
        for i, label in enumerate(labels):
            for changed in numeric_variants(label, start, end):
                copy = list(labels)
                copy[i] = changed
                yield tuple(copy)
    if keywords:
        for word in words:
            if not re.fullmatch(r'[a-z0-9-]{1,63}', word):
                continue
            for pos in range(len(labels) + 1):
                yield tuple(labels[:pos] + [word] + labels[pos:])
            for pos in range(len(labels)):
                copy = list(labels)
                copy[pos] = word
                yield tuple(copy)
            if numbers:
                for i, label in enumerate(labels):
                    for changed in numeric_variants(label, start, end):
                        copy = list(labels)
                        copy[i] = changed
                        for pos in range(len(copy) + 1):
                            yield tuple(copy[:pos] + [word] + copy[pos:])
                        for pos in range(len(copy)):
                            replaced = copy.copy()
                            replaced[pos] = word
                            yield tuple(replaced)


def main():
    p = argparse.ArgumentParser(description='LabelMorph: offline subdomain label shuffling, keyword insertion/replacement and numeric mutations')
    p.add_argument('-l', '--list', required=True, help='Input hostnames, one per line')
    p.add_argument('-d', '--domain', required=True, help='Fixed root domain, e.g. example.com')
    p.add_argument('-w', '--words', help='Optional keywords, one per line')
    p.add_argument('--start', type=int, default=0, help='Numeric range start (default: 0)')
    p.add_argument('--end', type=int, default=100, help='Numeric range end, inclusive (default: 100)')
    p.add_argument('--no-numbers', action='store_true', help='Disable numeric mutations')
    p.add_argument('--no-shuffle', action='store_true', help='Disable label permutations')
    p.add_argument('--no-keywords', action='store_true', help='Disable keyword insertion/replacement')
    p.add_argument('--limit', type=int, default=100000, help='Maximum unique candidates per input (default: 100000)')
    p.add_argument('-o', '--output', default='candidates.txt')
    a = p.parse_args()
    if a.start < 0 or a.end < a.start or a.limit < 1:
        p.error('Require 0 <= --start <= --end and --limit >= 1')
    root = a.domain.lower().strip('.')
    suffix = '.' + root
    words = list(dict.fromkeys(read_lines(a.words))) if a.words else []
    total = 0
    with open(a.output, 'w', encoding='utf-8') as out:
        for hostname in read_lines(a.list):
            if not hostname.endswith(suffix):
                print(f'[skip] Outside root domain: {hostname}')
                continue
            labels = hostname[:-len(suffix)].split('.')
            if not all(re.fullmatch(r'[a-z0-9-]{1,63}', x) for x in labels):
                print(f'[skip] Invalid hostname: {hostname}')
                continue
            seen = set()
            capped = False
            for candidate_labels in variants(labels, words, a.start, a.end, not a.no_numbers, not a.no_keywords):
                arrangements = set(itertools.permutations(candidate_labels)) if not a.no_shuffle else (candidate_labels,)
                for arrangement in arrangements:
                    candidate = '.'.join(arrangement) + suffix
                    if len(candidate) > 253 or candidate in seen:
                        continue
                    if len(seen) >= a.limit:
                        capped = True
                        break
                    seen.add(candidate)
                    out.write(candidate + '\n')
                    total += 1
                if capped:
                    break
            print(f'[+] {hostname}: {len(seen)} candidates' + (' (limit reached)' if capped else ''))
    print(f'[+] Wrote {total} candidates to {a.output}')
    print('[i] Output is offline candidate generation, not DNS validation. Duplicates across different inputs may occur.')


if __name__ == '__main__':
    main()
