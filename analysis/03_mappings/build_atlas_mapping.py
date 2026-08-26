"""
Build Google ATLAS (2026) Gemini usage mapping to STYRK-08.

IMPORTANT COARSENESS CAVEAT: Google has not published occupation-level
ATLAS data (dataset access is restricted; see atlas/README.md). The only
public quantitative table is Figure 1 of the report -- Gemini's share of
US work-related interactions per SOC 2018 MAJOR GROUP (22 groups) next
to the group's US employment share. This mapping therefore carries ONE
value per SOC major group: the representation ratio (interaction share /
employment share), a scale-free relative-usage measure analogous to
AEI's relative usage per occupation.

Every detailed SOC 2018 code inherits its major group's ratio and is
pushed through the standard SOC 2018 -> SOC 2010 -> ISCO-08 -> STYRK-08
chain (loaders and manual maps imported from build_eloundou_mapping.py).
A STYRK-08 code fed by SOC codes from several major groups gets a blend;
n_major_groups records how many groups contribute. There is NO genuine
4-digit variation in the source -- do not use this mapping for anything
finer than major-group contrasts, and do not build quintiles on it
(equal-frequency quintiles would split identical values arbitrarily, so
none are assigned).

Data source:
- atlas/atlas_v1_soc_major_gemini_shares_digitized_2026-07.csv:
  digitized from Figure 1 of Google AI & Economy Research Program,
  ATLAS v1.0 (July 2026, arXiv:2608.00038); +/-0.1 pp digitization
  error, see atlas/README.md for method and validation.

Crosswalk sources: same BLS files as build_eloundou_mapping.py.
"""

import csv                                   # plain CSV reading/writing
from pathlib import Path                     # filesystem-path handling
from collections import defaultdict         # accumulation

# Shared crosswalk loaders and Norway-specific manual maps.
from build_eloundou_mapping import (
    load_soc_2018_to_2010,
    load_soc2010_to_isco08,
    load_styrk08_codes,
    MANUAL_STYRK_MAP,
    MANUAL_STYRK_SOC_MAP,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root (3 levels up)
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'              # exposure-data folder

ATLAS_FILE = DATA_DIR / 'atlas' / 'atlas_v1_soc_major_gemini_shares_digitized_2026-07.csv'
OUTPUT_FILE = DATA_DIR / 'styrk08_atlas_mapping.csv'      # output mapping


def load_atlas_groups() -> dict[str, float]:
    """Load the representation ratio per 2-digit SOC major-group prefix."""
    ratios = {}
    with open(ATLAS_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            # '15-0000' -> prefix '15'.
            prefix = row['soc2018_major_group'].split('-')[0]
            ratios[prefix] = float(row['representation_ratio'])
    return ratios


def build_mapping():
    # ---- Load all inputs -------------------------------------------------
    print("Loading ATLAS major-group representation ratios...")
    group_ratio = load_atlas_groups()
    print(f"  {len(group_ratio)} SOC 2018 major groups with ratios")

    print("Loading SOC 2018 -> SOC 2010 crosswalk...")
    soc18_to_10 = load_soc_2018_to_2010()
    print(f"  {len(soc18_to_10)} SOC 2018 codes mapped")

    print("Loading SOC 2010 -> ISCO-08 crosswalk...")
    soc10_to_isco, partial_flags = load_soc2010_to_isco08()
    print(f"  {len(soc10_to_isco)} SOC 2010 codes mapped to ISCO-08")

    print("Loading STYRK-08 codes...")
    styrk_codes = load_styrk08_codes()
    print(f"  {len(styrk_codes)} valid STYRK-08 codes")

    # ---- Step 1: assign each SOC 2018 code its group ratio, walk to 2010 -
    # Accumulate per SOC 2010 code: ratio values and source major groups.
    soc2010_scores: dict[str, list[float]] = defaultdict(list)
    soc2010_groups: dict[str, set[str]] = defaultdict(set)
    # Count SOC 2018 codes whose major group has no ATLAS value (military).
    skipped_18 = 0
    for soc18 in soc18_to_10:
        prefix = soc18.split('-')[0]
        if prefix not in group_ratio:
            skipped_18 += 1
            continue
        for soc10 in soc18_to_10[soc18]:
            soc2010_scores[soc10].append(group_ratio[prefix])
            soc2010_groups[soc10].add(prefix)
    print(f"\n  SOC 2018 -> 2010: {len(soc2010_scores)} SOC 2010 codes, "
          f"{skipped_18} SOC 2018 codes without a group ratio (military)")

    # ---- Step 2: SOC 2010 -> ISCO-08 -------------------------------------
    # Collect per-ISCO contribution records (one per contributing SOC code).
    isco_contributions: dict[str, list[dict]] = defaultdict(list)
    unmapped_10 = 0
    for soc10, vals in soc2010_scores.items():
        # Average across the SOC 2018 sources feeding this 2010 code.
        avg = sum(vals) / len(vals)
        if soc10 in soc10_to_isco:
            fan_out = len(soc10_to_isco[soc10])
            for isco in soc10_to_isco[soc10]:
                is_partial = partial_flags.get((soc10, isco), False)
                isco_contributions[isco].append({
                    'ratio': avg,
                    'groups': soc2010_groups[soc10],
                    'soc': soc10,
                    'partial': is_partial,
                    'fan_out': fan_out if is_partial else 1,
                })
        else:
            unmapped_10 += 1
    print(f"  SOC 2010 -> ISCO-08: {len(isco_contributions)} ISCO-08 codes, "
          f"{unmapped_10} SOC 2010 codes unmapped")

    # ---- Step 3: filter to valid STYRK-08 codes and average --------------
    results = []
    for isco, contribs in sorted(isco_contributions.items()):
        if isco not in styrk_codes:
            continue
        # Union of contributing major groups (coarseness bookkeeping).
        groups = set().union(*(c['groups'] for c in contribs))
        results.append({
            'styrk08': isco,
            'atlas_repr_ratio': round(sum(c['ratio'] for c in contribs) / len(contribs), 4),
            'n_soc_matched': len(contribs),
            'n_major_groups': len(groups),
            'has_partial_match': 1 if any(c['partial'] for c in contribs) else 0,
            'max_partial_fanout': max((c['fan_out'] for c in contribs if c['partial']), default=0),
            'manual_map': '',
        })

    # ---- Manual SOC overrides (Norway-specific code collisions) ----------
    # Same overrides as the other mappings; the source value is just the
    # SOC code's major-group ratio (group 29 for both).
    manual_targets = set(MANUAL_STYRK_SOC_MAP)
    results = [r for r in results if r['styrk08'] not in manual_targets]
    for styrk_target, soc_sources in MANUAL_STYRK_SOC_MAP.items():
        if styrk_target not in styrk_codes:
            continue
        vals, groups, used_socs = [], set(), []
        for soc in soc_sources:
            lst = soc2010_scores.get(soc)
            if not lst:
                continue
            vals.append(sum(lst) / len(lst))
            groups |= soc2010_groups[soc]
            used_socs.append(soc)
        if not used_socs:
            print(f"  Manual SOC map skipped: {styrk_target} has no source ratio")
            continue
        results.append({
            'styrk08': styrk_target,
            'atlas_repr_ratio': round(sum(vals) / len(vals), 4),
            'n_soc_matched': len(used_socs),
            'n_major_groups': len(groups),
            'has_partial_match': 0,
            'max_partial_fanout': 0,
            'manual_map': 'SOC:' + ';'.join(used_socs),
        })
        print(f"  Manual SOC map: {styrk_target} <- {';'.join(used_socs)}")

    # ---- Manual STYRK-to-STYRK copies (nurses etc.) ----------------------
    mapped_codes = {r['styrk08'] for r in results}
    for styrk_target, styrk_source in MANUAL_STYRK_MAP.items():
        if styrk_target in mapped_codes or styrk_target not in styrk_codes:
            continue
        source_row = next((r for r in results if r['styrk08'] == styrk_source), None)
        if source_row:
            manual = dict(source_row)
            manual['styrk08'] = styrk_target
            manual['manual_map'] = styrk_source
            results.append(manual)
            print(f"  Manual map: {styrk_target} <- {styrk_source}")

    # Deterministic output order.
    results.sort(key=lambda r: r['styrk08'])

    print(f"\n  Final: {len(results)} STYRK-08 codes with an ATLAS group ratio")
    print(f"  Coverage: {len(results)}/{len(styrk_codes)} "
          f"({100*len(results)/len(styrk_codes):.1f}%)")
    # How many codes blend more than one major group (coarseness check).
    n_blend = sum(1 for r in results if r['n_major_groups'] > 1)
    print(f"  Codes blending >1 major group: {n_blend}")
    vals = [r['atlas_repr_ratio'] for r in results]
    print(f"  atlas_repr_ratio range: {min(vals):.3f} - {max(vals):.3f}")

    # ---- Save ------------------------------------------------------------
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'styrk08', 'atlas_repr_ratio', 'n_soc_matched', 'n_major_groups',
            'has_partial_match', 'max_partial_fanout', 'manual_map',
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == '__main__':
    build_mapping()
