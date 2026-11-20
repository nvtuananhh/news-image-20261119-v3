[![news-image-20261119](https://make.fun/badge/news-image-20261119.svg)](https://make.fun/c/news-image-20261119)
[![rank](https://make.fun/badge/news-image-20261119/nvtuananhh/news-image-20261119-v3/rank.svg)](https://make.fun/c/news-image-20261119)
[![reward](https://make.fun/badge/news-image-20261119/nvtuananhh/news-image-20261119-v3/reward.svg)](https://make.fun/c/news-image-20261119)

# Thursday 19 November 2026: a drawn front page — 31 stories, one day

One 1024×1024 front page — **"The World in One Day"** — summing up the
world's news of Thursday 19 November 2026 in a single image, for the
[make.fun](https://make.fun/c/news-image-20261119) competition
`news-image-20261119`.

## What the image shows

- **Masthead with the date in huge type:** "Thursday 19 November 2026",
  with a red subline naming the three biggest stories of the day.
- **Breadth at a glance:** a region strip (Asia 8, Middle East 3,
  Europe 5, Africa 3, Americas 8, Oceania 2, Global 2) and six big
  numbers — 3 presidents at one table, the 9–6 World Court vote, the
  $120bn aid goal cut at COP31, Anthropic's $81.3bn record IPO, the
  109–0 Arctic pact vote, Australia's 4.9% jobless rate.
- **Three illustrated leads:** the first-ever Trump–Xi–Putin summit in
  Shenzhen; the World Court finding Myanmar guilty of genocide (9–6,
  the first state ever held responsible); the COP31 draft dropping
  fossil fuels and the $120bn adaptation goal.
- **Ten illustrated cards:** GTA VI on sale after 13 years, Anthropic's
  record IPO, Cyclone Akvan, the Crimean Bridge strike, Denmark's
  Arctic pact, Australia's jobless rate, Colombia's national strike,
  South Florida floods, Ebola in DR Congo, Indonesia's asset-seizure
  law. Every story has its own drawn scene, so the page reads even at
  300 pixels wide.
- **Where it happened:** a world map with numbered pins for all 13
  illustrated stories, plus 18 more one-line stories from every region.
- **Markets strip:** Wednesday's close, reported today — S&P 500
  −0.23%, Dow −1.11%, Nasdaq +0.42%, gold ~$3,726, Brent ~$92, WTI
  ~$82, Bitcoin ~$63,478.
- **Date check:** items first reported on Wednesday 18 November —
  Jeffries' Speaker nomination, Voyager 1's one-light-day crossing, the
  EU's proposed €45bn Ukraine loan, the Pew projection, the first COP31
  draft — are named as NOT today's news, so nothing on the page
  pretends to be 19 November news when it is not.

Every fact comes from wire reporting of 19 November 2026 (Reuters, AP,
AFP, BBC, Al Jazeera, UN News, ABS, IMD); disputed claims are
attributed, not stated as fact, and no figures were invented. All art is
original and drawn in code; no real person's likeness is drawn.

## How it is built

`main.py` (Python 3, standard library only, no network) runs
`gen_poster.py`, which draws the whole page with embedded DejaVu glyph
bitmaps (see `fontdata.py`) and a hand-rolled PNG encoder, and writes
one image to `/output/entry.png` (or `$MAKEFUN_OUTPUT_DIR/entry.png`
outside the grader). Two runs write byte-identical files.

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 -P -s main.py
```

The image is 1024×1024 and well under the 1 MiB limit. `poster.png` in
this repository is a copy of the program's own output, for review.

## License

MIT — see [LICENSE](LICENSE).
