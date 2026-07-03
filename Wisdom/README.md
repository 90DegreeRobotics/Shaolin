# The Wisdom Corpus

Chirox the sage grounds its teaching in real, public-domain texts and cites them.
It does not fabricate quotations or attributions — the wisdom is checkable, not
invented in the voice of a dead master. This is the honest form of a sage.

## Texts

Fetched once from Project Gutenberg into `Wisdom/texts/` (git-ignored; raw dumps),
fully offline thereafter. All are in the public domain.

| Text | Tradition | Source |
|---|---|---|
| Tao Te Ching (*The Tao Teh King*, Legge 1891) | Daoism | Project Gutenberg #216 |
| Chuang Tzu: Mystic, Moralist, and Social Reformer | Daoism | Project Gutenberg #59709 |
| The Analects of Confucius (Legge) | Confucianism | Project Gutenberg #3330 |
| Chinese Literature: Confucius and Mencius | Confucianism | Project Gutenberg #10056 |
| The Dhammapada (Müller) | Buddhism | Project Gutenberg #2017 |
| The Gospel of Buddha (Carus) | Buddhism | Project Gutenberg #35895 |
| The Light of Asia (Arnold) | Buddhism | Project Gutenberg #8920 |
| The Art of War (Giles 1910) | Strategy | Project Gutenberg #132 |

All eight are downloaded and loaded (verified 2026-07-03: 7,272 passages ground
the sage). The narrator also reads them aloud: "Chirox, read me the tao te ching."

## Fetch

The texts download automatically the first time Chirox the sage is used. To fetch
them manually:

```python
python -c "from chirox.wisdom import ensure_corpus; print('fetched:', ensure_corpus())"
```

## Notes

- These are older public-domain translations, chosen because they are free and
  unencumbered — not because they are the finest modern renderings. Verify any line
  you intend to lean on; several terms (Dao, Ren, Wu Wei) flatten in translation.
- More texts (the I Ching, Lieh-Tzu, further Buddhist suttas) can be added to the
  `CORPUS` manifest in `chirox/wisdom.py` as public-domain sources are confirmed
  (IDs verified against the Gutendex catalog before adding — never guessed).
- A future sage-voice LoRA may tune *cadence and style*; it will never be a source
  of facts. Facts always come from these retrieved passages.
