// Faithful port of the ratio() computation from Python's difflib.SequenceMatcher
// (Ratcliff/Obershelp / Gestalt pattern matching).
//
// The Python engine uses difflib.SequenceMatcher(None, a, b).ratio() in three
// places (sponsor matcher _score_names, _token_similarity, _has_weak_token_
// alignment). We reproduce CPython's algorithm exactly:
//   - find_longest_match using the b2j index + the "junk" / "popular" handling,
//   - recursive get_matching_blocks,
//   - ratio() = 2.0 * M / T where M is total matched length, T = len(a)+len(b).
//
// Notes on equivalence:
//   * We pass isjunk = None (as the Python engine does), so bjunk is empty.
//   * CPython's "autojunk" heuristic marks a character of b as popular when
//     len(b) >= 200 AND it occurs more than 1% of len(b). All employer-name
//     strings in this product are far shorter than 200 chars, so autojunk never
//     fires. We still implement it for completeness so the port is exact.

class SequenceMatcher {
  private a: string;
  private b: string;
  private b2j: Map<string, number[]>;
  private bpopular: Set<string>;

  constructor(a: string, b: string) {
    this.a = a;
    this.b = b;
    this.b2j = new Map();
    this.bpopular = new Set();
    this.chainB();
  }

  private chainB(): void {
    const b = this.b;
    const b2j = this.b2j;
    for (let i = 0; i < b.length; i += 1) {
      const elt = b[i];
      const indices = b2j.get(elt);
      if (indices) {
        indices.push(i);
      } else {
        b2j.set(elt, [i]);
      }
    }

    // isjunk is None -> no junk set.

    // autojunk heuristic (CPython): for b of length >= 200, treat any element
    // occurring more than 1% of len(b) as "popular" and remove it from b2j.
    const n = b.length;
    if (n >= 200) {
      const ntest = Math.floor(n / 100) + 1;
      const popular = this.bpopular;
      for (const [elt, idxs] of b2j) {
        if (idxs.length > ntest) {
          popular.add(elt);
        }
      }
      for (const elt of popular) {
        b2j.delete(elt);
      }
    }
  }

  findLongestMatch(
    alo: number,
    ahi: number,
    blo: number,
    bhi: number
  ): [number, number, number] {
    const a = this.a;
    const b2j = this.b2j;
    let besti = alo;
    let bestj = blo;
    let bestsize = 0;

    let j2len = new Map<number, number>();

    for (let i = alo; i < ahi; i += 1) {
      const newj2len = new Map<number, number>();
      const indices = b2j.get(a[i]);
      if (indices) {
        for (const j of indices) {
          if (j < blo) continue;
          if (j >= bhi) break;
          const k = (j2len.get(j - 1) || 0) + 1;
          newj2len.set(j, k);
          if (k > bestsize) {
            besti = i - k + 1;
            bestj = j - k + 1;
            bestsize = k;
          }
        }
      }
      j2len = newj2len;
    }

    // Extend the best match to include adjacent equal elements. With isjunk
    // None and no junk, only the non-junk extension loops run.
    while (
      besti > alo &&
      bestj > blo &&
      a[besti - 1] === this.b[bestj - 1]
    ) {
      besti -= 1;
      bestj -= 1;
      bestsize += 1;
    }
    while (
      besti + bestsize < ahi &&
      bestj + bestsize < bhi &&
      a[besti + bestsize] === this.b[bestj + bestsize]
    ) {
      bestsize += 1;
    }

    return [besti, bestj, bestsize];
  }

  getMatchingBlocks(): [number, number, number][] {
    const la = this.a.length;
    const lb = this.b.length;

    const queue: [number, number, number, number][] = [[0, la, 0, lb]];
    const matchingBlocks: [number, number, number][] = [];

    while (queue.length > 0) {
      const [alo, ahi, blo, bhi] = queue.pop()!;
      const [i, j, k] = this.findLongestMatch(alo, ahi, blo, bhi);
      if (k > 0) {
        matchingBlocks.push([i, j, k]);
        if (alo < i && blo < j) {
          queue.push([alo, i, blo, j]);
        }
        if (i + k < ahi && j + k < bhi) {
          queue.push([i + k, ahi, j + k, bhi]);
        }
      }
    }

    matchingBlocks.sort((x, y) => {
      if (x[0] !== y[0]) return x[0] - y[0];
      if (x[1] !== y[1]) return x[1] - y[1];
      return x[2] - y[2];
    });

    // CPython appends a sentinel and collapses adjacent blocks; for ratio() we
    // only need the total matched size, so the sentinel/collapse step does not
    // change the sum. We skip it.
    return matchingBlocks;
  }

  ratio(): number {
    let matches = 0;
    for (const [, , size] of this.getMatchingBlocks()) {
      matches += size;
    }
    return calculateRatio(matches, this.a.length + this.b.length);
  }
}

function calculateRatio(matches: number, length: number): number {
  if (length) {
    return (2.0 * matches) / length;
  }
  return 1.0;
}

/** Equivalent to difflib.SequenceMatcher(None, a, b).ratio(). */
export function sequenceRatio(a: string, b: string): number {
  return new SequenceMatcher(a, b).ratio();
}
