# LabelMorph

**LabelMorph** is an offline subdomain candidate generator for authorized DNS reconnaissance. It creates new hostnames from existing ones using DNS label shuffling, keyword insertion and replacement, numeric mutation, and combinations of these techniques.

> **Important:** LabelMorph does **not** check DNS records. Its output contains **guesses**, not confirmed subdomains. Resolve candidates in a separate validation step and test only domains you own or are explicitly authorized to assess.

## Features

- **Shuffle subdomain labels:** `www.test265.stage.example.com` → `stage.test265.www.example.com`
- **Insert keywords:** `lorem.example.com` + `dev` → `lorem.dev.example.com` or `dev.lorem.example.com`
- **Replace labels:** `store.data.news.example.com` + `admin` → `store.data.admin.example.com`
- **Mutate standalone numbers:** `1.example.com` → `2.example.com`
- **Mutate embedded numbers:** `h1.example.com` → `h2.example.com`; `stage2p2488.example.com` → `stage2p2489.example.com`
- **Combine techniques:** numeric changes and keyword insertion/replacement followed by label shuffling
- **Preserve leading zero width** for numbers starting with `0`, e.g. `test007` → `test008`
- **Restrict output to a fixed root domain** and cap candidate generation per input hostname

## Requirements

- Python 3.8+ (standard library only; no pip dependencies)
- Optional: [ProjectDiscovery dnsx](https://github.com/projectdiscovery/dnsx) for DNS validation

## Installation

Save `labelmorph.py` in your working directory (you can rename it `labelmorph.py`):

```bash
python3 labelmorph.py -h
```

## Usage

### Generate all mutation types

```bash
python3 labelmorph.py -l subdomains.txt -d example.com -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt --start 0  --end 1000 -o candidates.txt
```

Shuffling, numeric mutations, and keyword insertion/replacement are enabled by default. The `--end` value is inclusive. If the source labels include numbers higher than 1000, increase the range as appropriate.

### Shuffle existing labels only

```bash
python3 labelmorph.py -l subdomains.txt -d example.com \
  --no-numbers --no-keywords -o shuffled.txt
```

### Numeric mutations only

```bash
python3 labelmorph.py -l subdomains.txt -d example.com \
  --start 0 --end 1000 --no-shuffle --no-keywords -o numeric.txt
```

### Keyword insertion/replacement with shuffling

```bash
python3 labelmorph.py -l subdomains.txt -d example.com \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt --no-numbers -o keyword_candidates.txt
```

### CLI options

| Option | Description |
| --- | --- |
| `-l, --list` | Required input hostname file, one per line |
| `-d, --domain` | Required fixed root domain, such as `example.com` |
| `-w, --words` | Optional keyword file, one word per line |
| `--start` | Numeric range start; default `0` |
| `--end` | Numeric range end, inclusive; default `100` |
| `--no-numbers` | Disable numeric mutations |
| `--no-shuffle` | Disable label permutations |
| `--no-keywords` | Disable keyword insertion and replacement |
| `--limit` | Maximum unique candidates **per input hostname**; default `100000` |
| `-o, --output` | Output file; default `candidates.txt` |
| `-h, --help` | Show help and exit |

## Validate candidates with DNS tools

**Generation is not validation.** After generating candidates, check which names actually resolve in DNS. Run DNS queries only against authorized domains and at a rate permitted by the relevant program or infrastructure owner.

### 1. Deduplicate the output

```bash
sort -u candidates.txt > candidates_unique.txt
wc -l candidates_unique.txt
```

This matters because the generator deduplicates **within** each input hostname, but candidates generated from different input hostnames can overlap.

### 2. Install dnsx

```bash
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
```

Make sure your Go binary directory is in `PATH` (often `~/go/bin`).

### 3. Resolve generated candidates

```bash
dnsx -l candidates_unique.txt -silent -rl 20 -o resolved.txt
```

`resolved.txt` contains hostnames that returned DNS answers under dnsx's default resolution behavior. This is **not** proof that a website is reachable, that a service is running, or that the hostname is in scope.

For A-record answers with returned addresses:

```bash
dnsx -l candidates_unique.txt -a -resp -silent -rl 20 -o resolved_with_ips.txt
```

### 4. Check for wildcard DNS

Some DNS zones resolve arbitrary nonexistent names. Test a few random, unlikely hostnames under the same relevant parent zone and compare their responses with your candidates. Do not treat a wildcard response alone as proof that a discovered service exists. dnsx supports wildcard filtering; consult its [documentation](https://github.com/projectdiscovery/dnsx) for the options appropriate to your environment.

### 5. Review results

```bash
wc -l candidates_unique.txt resolved.txt
head -20 resolved.txt
```

**Suggested workflow:** known in-scope subdomains → LabelMorph → deduplicate → dnsx → wildcard review → manually verify relevant hosts.

## Performance and limitations

- Label permutations grow factorially: 3 unique labels have 6 permutations; 6 labels have 720.
- Large numeric ranges combined with keyword lists can generate millions of candidates. Start with a small `--end` and `--limit`.
- `--limit` is per input hostname, **not** a global file limit.
- The script writes output incrementally but maintains a per-input deduplication set and materializes permutations for each candidate; very large runs can still consume significant RAM.
- It mutates one numeric sequence at a time; it does not exhaustively mutate multiple numeric sequences simultaneously.
- It preserves the root domain specified by `-d` and skips input hostnames outside that root.
- DNS resolution does not establish ownership, scope authorization, or an exploitable vulnerability.
