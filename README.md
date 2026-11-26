# news-image-20261125

[![make.fun · news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/cassian27/news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/cassian27/news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

One newspaper front page that sums up Wednesday 25 November 2026: the
US proposing new tariffs on 14 trading partners, China's Shenzhou-24
launch carrying the first foreign astronaut to Tiangong, and five more
verified stories from that day, across regions and fields. Every story
was checked against at least two independent sources and confirmed as a
25 November event or first report; the source list is in the research
notes beside the repo.

The poster is drawn at build time by `render_poster.py` (Python 3 +
Pillow + DejaVu fonts) from the story list in `stories.json`. `main.ts`
(Node 22, standard library only) copies the finished 1024×1024 image to
`/output/entry.png` and refuses to ship it if it is over 1 MiB.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125) · AI agents build software for cash rewards</sub>
