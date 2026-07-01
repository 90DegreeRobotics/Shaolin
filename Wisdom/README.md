# The Wisdom Corpus

Chirox the sage grounds its teaching in real, public-domain texts and cites them.
It does not fabricate quotations or attributions — the wisdom is checkable, not
invented in the voice of a dead master. This is the honest form of a sage.

## Texts

Fetched once from Project Gutenberg into `Wisdom/texts/` (git-ignored; raw dumps),
fully offline thereafter. All are in the public domain.

| Text | Translator | Source |
|---|---|---|
| Tao Te Ching (*The Tao Teh King*) | James Legge (1891) | Project Gutenberg #216 |
| The Analects of Confucius | James Legge | Project Gutenberg #3330 |
| The Dhammapada | F. Max Müller | Project Gutenberg #2017 |
| The Art of War | Lionel Giles (1910) | Project Gutenberg #132 |

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
- More texts (Zhuangzi, the I Ching, further Buddhist suttas) can be added to the
  `CORPUS` manifest in `chirox/wisdom.py` as public-domain sources are confirmed.
- A future sage-voice LoRA may tune *cadence and style*; it will never be a source
  of facts. Facts always come from these retrieved passages.
