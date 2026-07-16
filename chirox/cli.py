"""Chirox command line — one gate to all three organs.

    chirox init                       establish the operator + config (sealed)
    chirox today                      where you stand, and today's gate
    chirox log <type> [--file F]      fill or ingest a Dojo Record entry
    chirox library                    list readable docs/books Chirox can narrate
    chirox vision --source 0 [--seal] run the deterministic reflex
    chirox review                     today's due review template
    chirox debrief [--question "…"]   the Master speaks, from evidence
    chirox verify                     check the Codex chain (Forever Law)

Writes go through the Sentinel (fail-closed) and are sealed into the append-only
Codex. The Master never fabricates: if the local model is down, he says so.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from chirox.calendar import dojo_day
from chirox.config import CODEX_PATH, Config, ensure_data_dir
from chirox.curriculum import Curriculum
from chirox.record.codex import Codex
from chirox.record.ingest import blank_template, commit_record, ingest_file
from chirox.record.schema import RECORD_CLASSES
from chirox.sentinel import Sentinel

RULE = "-" * 64
LOG_TYPES = {"daily": "daily_checkin", "weekly": "weekly_review",
             "monthly": "monthly_checkpoint", "mandarin": "mandarin_journal"}


def _bootstrap() -> tuple[Config, Codex, Sentinel]:
    ensure_data_dir()
    config = Config.load()
    codex = Codex(CODEX_PATH)
    sentinel = Sentinel(codex, config)
    return config, codex, sentinel


def _prefill(record_type: str, today: date, day_number: int, week_number: int) -> dict:
    ov: dict = {}
    cls = RECORD_CLASSES[record_type]
    f = cls.__dataclass_fields__
    if "date" in f:
        ov["date"] = today.isoformat()
    if "day_number" in f:
        ov["day_number"] = day_number
    if "week_number" in f:
        ov["week_number"] = week_number
    return ov


# --- commands ------------------------------------------------------------------


def cmd_init(args) -> int:
    config, codex, sentinel = _bootstrap()
    grant = sentinel.init_operator()  # establish the operator before any sealed change
    if args.start:
        try:
            date.fromisoformat(args.start)
        except ValueError:
            print(f"--start must be an ISO date (YYYY-MM-DD), got {args.start!r}", file=sys.stderr)
            return 2
        previous = config.practice_start
        if args.start != previous:
            # Forever Law: a change to the meaning of the whole year is recorded, not silent.
            g = sentinel.authorize("config.practice_start_set")
            config.practice_start = args.start
            config.save()
            codex.append("practice_start_set", {"date": args.start, "previous": previous})
            sentinel.consume(g)
            print(f"(start date corrected {previous} -> {args.start}, sealed)")
    print(RULE)
    print("CHIROX — the path is opened.")
    print(f"  Practice start (day 1): {config.practice_start}")
    print(f"  Master model:           {config.model}  (local, offline)")
    print(f"  Sentinel mode:          {config.sentinel_mode}")
    if grant:
        print(f"  Operator established and sealed at seq {grant.decision_seq}.")
    else:
        print("  Operator already established.")
    print(RULE)
    return 0


def cmd_today(args) -> int:
    config, codex, _ = _bootstrap()
    cur = Curriculum()
    d = dojo_day(config.practice_start_date)
    print(RULE)
    print(d.headline())
    if d.phase_focus:
        print("Focus: " + d.phase_focus)
    inv = cur.daily_invariant()
    if inv:
        print("\nTODAY'S GATE — the daily invariant:")
        print(inv.excerpt(600))
    if d.is_checkpoint:
        print("\n>>> Checkpoint day. Write the long review:  chirox log monthly")
    elif d.is_weekly_review:
        print("\n>>> Sunday. Close the week:  chirox log weekly")
    print(RULE)
    return 0


def cmd_log(args) -> int:
    config, codex, sentinel = _bootstrap()
    record_type = LOG_TYPES[args.type]

    if args.print_template:
        print(blank_template(record_type))
        return 0

    d = dojo_day(config.practice_start_date)
    overrides = _prefill(record_type, date.today(), d.day_number, d.week_number)

    if not args.file:
        # Drop a prefilled template into the inbox for the practitioner to fill.
        inbox = ensure_data_dir() / "inbox"
        inbox.mkdir(exist_ok=True)
        text = blank_template(record_type)
        for label, val in (("Date:", overrides.get("date")),
                           ("Day number:", overrides.get("day_number")),
                           ("Week number:", overrides.get("week_number"))):
            if val is not None:
                text = text.replace(label + "\n", f"{label} {val}\n")
        out = inbox / f"{record_type}_{date.today().isoformat()}.md"
        out.write_text(text, encoding="utf-8")
        print(f"Template ready: {out}")
        print(f"Fill it, then:   chirox log {args.type} --file \"{out}\"")
        return 0

    sentinel.init_operator()
    record = ingest_file(args.file, record_type, overrides=overrides)
    event = commit_record(record, codex, sentinel)
    print(f"Sealed {record_type} into the Dojo Record at seq {event.seq} (hash {event.hash[:12]}…).")
    return 0


def cmd_vision(args) -> int:
    from chirox.vision.pipeline import run_session

    session = run_session(source=args.source, stance=args.stance, seconds=args.seconds,
                          show=not args.no_show, seal=args.seal)
    print(json.dumps(session.payload(), indent=2))
    if args.seal:
        print("\nSealed the deterministic session into the Dojo Record.")
    return 0


def cmd_record(args) -> int:
    from chirox.vision.recorder import record_session

    rec = record_session(exercise=args.exercise, source=args.source, seconds=args.seconds,
                         stance=args.stance, show=not args.no_show, seal=not args.no_seal)
    print(json.dumps(rec.payload(), indent=2))
    print(f"\nSaved video: {rec.video_path}")
    if not args.no_seal:
        print("Sealed the recording manifest into the Dojo Record (video stays in the private archive).")
    return 0


def cmd_timeline(args) -> int:
    _, codex, _ = _bootstrap()
    recs = list(codex.events("session_recording"))
    if args.exercise:
        recs = [e for e in recs if e.payload.get("exercise") == args.exercise]
    if not recs:
        which = f" of {args.exercise}" if args.exercise else ""
        print(f"No recordings{which} yet. Start one:  chirox record --exercise eight_brocades")
        return 0
    label = f" of {args.exercise}" if args.exercise else ""
    print(f"Visual timeline{label} — {len(recs)} session(s), oldest first:")
    for e in recs:
        p = e.payload
        print(f"  day {p['day_number']:>3}  {p['date']}  {p['exercise']:<16} "
              f"{p['duration_s']:>6}s  conf={p['mean_confidence']}  {p['video_path']}")
    return 0


def cmd_review(args) -> int:
    config, _, _ = _bootstrap()
    d = dojo_day(config.practice_start_date)
    if d.is_checkpoint:
        print(f"Monthly checkpoint (day {d.day_number}):\n")
        print(blank_template("monthly_checkpoint"))
    else:
        print(f"Weekly review (week {d.week_number}):\n")
        print(blank_template("weekly_review"))
    return 0


def cmd_library(args) -> int:
    """List the local spoken library without starting narration."""
    from chirox.narrator import readable_catalog, reading_progress

    progress = reading_progress()
    items = []
    for label, _keys, path in readable_catalog():
        items.append({
            "label": label,
            "kind": "book" if path.suffix == ".txt" else "doc",
            "file": path.name,
            "bookmark": progress.get(path.name, 0),
            "present": path.exists(),
        })
    if args.json:
        print(json.dumps({"items": items}, indent=2))
        return 0
    print("Readable library:")
    for item in items:
        mark = f" @ passage {item['bookmark']}" if item["bookmark"] else ""
        print(f"  - {item['label']} [{item['kind']}] ({item['file']}){mark}")
    return 0


def cmd_debrief(args) -> int:
    from chirox.master.brain import MasterUnavailable, debrief

    config, _, _ = _bootstrap()
    try:
        text = debrief(config, question=args.question)
    except MasterUnavailable as exc:
        print(f"The Master is silent — he will not fabricate.\n  {exc}", file=sys.stderr)
        return 2
    print(RULE)
    print(text)
    print(RULE)
    _speak(text, args.speak)
    return 0


def _speak(text: str, enabled: bool) -> None:
    if not enabled:
        return
    try:
        from chirox.voice import Voice

        Voice().speak(text)
    except Exception as exc:  # never let a voice hiccup break the text path
        print(f"(voice unavailable: {exc})", file=sys.stderr)


def cmd_say(args) -> int:
    from chirox.voice import Voice

    Voice().speak(args.text, play=not args.no_play)
    return 0


def cmd_train(args) -> int:
    from chirox.trainer import run_training

    result = run_training(
        source=int(args.source) if str(args.source).isdigit() else args.source,
        stances=args.stances.split(",") if args.stances else None,
        seconds=args.seconds, n=args.drills,
        speak=not args.no_speak, seal=not args.no_seal,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_narrate(args) -> int:
    from chirox.narrator import main as narrator_main

    argv = []
    if args.path:
        argv.append(args.path)
    if args.text:
        argv += ["--text", args.text]
    if args.voice:
        argv += ["--voice", args.voice]
    if args.pace:
        argv += ["--pace", str(args.pace)]
    if args.start:
        argv += ["--from", str(args.start)]
    if args.out:
        argv += ["--out", args.out]
    return narrator_main(argv)


def cmd_listen(args) -> int:
    from chirox.listener import ChiroxEar, LiveExchangeWitness, self_test

    if args.self_test:
        return 0 if self_test(witness=args.witness) else 1
    ear = ChiroxEar(device=args.device, speak_replies=not args.no_speak)
    witness = None
    if args.once or args.witness:
        witness = LiveExchangeWitness(device=args.device, aliases=ear.aliases,
                                      whisper_model=ear.config.whisper_model,
                                      samplerate=ChiroxEar.SAMPLERATE)
    ear.run(once=args.once, witness=witness)
    return 0


def cmd_sage(args) -> int:
    from chirox.master.brain import Ollama
    from chirox.master.sage import pose_question, reflect, seal_dialogue
    from chirox.wisdom import WisdomLibrary, ensure_corpus

    config, _, _ = _bootstrap()
    ensure_corpus()
    wisdom = WisdomLibrary()
    if not wisdom.passages:
        print("The wisdom corpus is not present and could not be fetched (offline?).", file=sys.stderr)
        return 2
    ollama = Ollama(config)
    ok, reason = ollama.available()
    if not ok:
        print(f"Chirox is silent — he will not fabricate.\n  {reason}", file=sys.stderr)
        return 2

    probe = pose_question(config, wisdom, topic=args.topic, ollama=ollama)
    print(RULE)
    print(probe.text)
    if probe.citations:
        print(f"\n  — grounded in: {', '.join(probe.citations)}")
    print(RULE)
    _speak(probe.text, args.speak)

    if args.listen:
        from chirox.voice import Voice

        print(f"\nSpeak your answer ({args.listen}s) …")
        answer = Voice().listen(seconds=float(args.listen))
        print(f"(heard) {answer}")
    else:
        answer = args.answer if args.answer is not None else input("\nYour answer (Chirox is listening):\n> ")
    if not answer.strip():
        print("No answer given. The question keeps.")
        return 0

    dlg = reflect(config, wisdom, probe, answer, ollama=ollama)
    print(RULE)
    print(dlg.reflection)
    print(f"\n[growth: {dlg.growth_marker} | themes: {', '.join(dlg.themes)}]")
    print(RULE)
    _speak(dlg.reflection, args.speak)
    ev = seal_dialogue(dlg, config)
    print(f"Sealed into your growth ledger (seq {ev.seq}).")
    return 0


def cmd_growth(args) -> int:
    from chirox.master.sage import growth_summary

    _, codex, _ = _bootstrap()
    g = growth_summary(codex)
    if not g["count"]:
        print("No sage dialogues yet. Sit with one:  chirox sage")
        return 0
    print(f"Growth ledger — {g['count']} dialogue(s).")
    if g["growth"]:
        print("  engagement:", ", ".join(f"{k}: {v}" for k, v in g["growth"].items()))
    if g["themes"]:
        print("  themes explored:")
        for theme, n in g["themes"][:15]:
            print(f"    {n:>2}x  {theme}")
    return 0


def cmd_verify(args) -> int:
    _, codex, _ = _bootstrap()
    ok, err = codex.verify()
    n = len(list(codex.events()))
    if ok:
        print(f"Codex intact: {n} sealed events, chain verified (Forever Law holds).")
        return 0
    print(f"CODEX BROKEN: {err}", file=sys.stderr)
    return 1


def cmd_memory(args) -> int:
    """What the Master can recall — and what has been withdrawn."""
    _, codex, _ = _bootstrap()
    forgotten = {e.payload.get("target_seq") for e in codex.events("forget")}
    convs = list(codex.events("conversation"))
    if not convs:
        print("No conversations sealed yet.")
        return 0
    shown = convs[-args.last:] if args.last else convs
    print(f"Sealed conversations ({len(convs)} total). The Master recalls all but the forgotten:")
    for e in shown:
        mark = "  [FORGOTTEN]" if e.seq in forgotten else ""
        q = " ".join(str(e.payload.get("question", "")).split())
        a = " ".join(str(e.payload.get("answer", "")).split())
        print(f"  seq {e.seq:>4}  {e.ts[:16]}{mark}")
        print(f"    Student: {q[:120]}")
        print(f"    Chirox:  {a[:120]}")
    return 0


def cmd_forget(args) -> int:
    config, codex, sentinel = _bootstrap()
    target = next((e for e in codex.events() if e.seq == args.seq), None)
    if target is None:
        print(f"No event at seq {args.seq}.", file=sys.stderr)
        return 2
    sentinel.init_operator()
    grant = sentinel.authorize("record.forget")
    event = codex.forget(args.seq, args.reason, operator=config.operator_id)
    sentinel.consume(grant)
    print(f"Sealed the forgetting of seq {args.seq} at seq {event.seq}.")
    print("The event stays in the chain (erasure is recorded, never silent); "
          "the Master will no longer recall it.")
    return 0


# --- parser --------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="chirox", description="Chirox — the deterministic Shaolin Master")
    sub = p.add_subparsers(dest="command", required=True)

    ini = sub.add_parser("init", help="establish operator + config")
    ini.add_argument("--start", help="ISO date the path began (day 1); defaults to today")
    ini.set_defaults(func=cmd_init)
    sub.add_parser("today", help="where you stand, and today's gate").set_defaults(func=cmd_today)

    lg = sub.add_parser("log", help="fill or ingest a Dojo Record entry")
    lg.add_argument("type", choices=sorted(LOG_TYPES))
    lg.add_argument("--file", help="a filled template to ingest")
    lg.add_argument("--print-template", action="store_true", help="print the blank template and exit")
    lg.set_defaults(func=cmd_log)

    vs = sub.add_parser("vision", help="run the deterministic reflex")
    vs.add_argument("--source", default="0", help="webcam index or video path")
    vs.add_argument("--stance", default="horse")
    vs.add_argument("--seconds", type=float, default=None)
    vs.add_argument("--no-show", action="store_true")
    vs.add_argument("--seal", action="store_true", help="seal the session into the Dojo Record")
    vs.set_defaults(func=cmd_vision)

    rc = sub.add_parser("record", help="record a training session to the visual timeline")
    rc.add_argument("--exercise", required=True, help="e.g. eight_brocades, horse_stance")
    rc.add_argument("--source", default="0", help="webcam index or video path")
    rc.add_argument("--seconds", type=float, default=None)
    rc.add_argument("--stance", default=None, help="optional static stance to also assess (horse|bow)")
    rc.add_argument("--no-show", action="store_true", help="run headless (no window)")
    rc.add_argument("--no-seal", action="store_true", help="do not seal a manifest into the Codex")
    rc.set_defaults(func=cmd_record)

    tl = sub.add_parser("timeline", help="list recorded sessions in order")
    tl.add_argument("--exercise", default=None, help="filter to one exercise")
    tl.set_defaults(func=cmd_timeline)

    sub.add_parser("review", help="today's due review template").set_defaults(func=cmd_review)

    db = sub.add_parser("debrief", help="the Master speaks, from evidence")
    db.add_argument("--question", help="ask the Master something specific")
    db.add_argument("--speak", action="store_true", help="speak the debrief aloud (Piper)")
    db.set_defaults(func=cmd_debrief)

    sg = sub.add_parser("sage", help="a grounded philosophical dialogue with Chirox")
    sg.add_argument("--topic", default=None, help="e.g. non-striving, fear, discipline")
    sg.add_argument("--answer", default=None, help="answer non-interactively (else prompts)")
    sg.add_argument("--speak", action="store_true", help="Chirox speaks the question + reflection")
    sg.add_argument("--listen", type=float, default=None, metavar="SECS",
                    help="answer by voice: record SECS and transcribe (Whisper)")
    sg.set_defaults(func=cmd_sage)

    sub.add_parser("growth", help="your wisdom growth ledger").set_defaults(func=cmd_growth)

    lb = sub.add_parser("library", help="list readable docs/books Chirox can narrate")
    lb.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    lb.set_defaults(func=cmd_library)

    tr = sub.add_parser("train", help="Chirox calls the drills aloud and measures your form")
    tr.add_argument("--source", default="0", help="camera index")
    tr.add_argument("--stances", default=None, help="comma list, e.g. horse,crane (default: Chirox chooses)")
    tr.add_argument("--seconds", type=int, default=60, help="seconds per drill")
    tr.add_argument("--drills", type=int, default=3, help="drill count when Chirox chooses")
    tr.add_argument("--no-speak", action="store_true", help="silent (text only)")
    tr.add_argument("--no-seal", action="store_true", help="do not seal the session")
    tr.set_defaults(func=cmd_train)

    na = sub.add_parser("narrate", help="read a long text aloud, audiobook style")
    na.add_argument("path", nargs="?", help="text or markdown file to read")
    na.add_argument("--text", default=None, help="read this literal text instead")
    na.add_argument("--voice", default=None, help="Piper voice override")
    na.add_argument("--pace", type=float, default=None, help="1.0 conversational; higher = slower")
    na.add_argument("--from", dest="start", type=int, default=None, metavar="N",
                    help="resume from chunk N")
    na.add_argument("--out", default=None, help="render to a WAV instead of playing")
    na.set_defaults(func=cmd_narrate)

    ls = sub.add_parser("listen", help="the always-on ear: wake word 'Chirox'")
    ls.add_argument("--device", type=int, default=None, help="input device index")
    ls.add_argument("--once", action="store_true", help="hold until one addressed exchange completes, then exit")
    ls.add_argument("--self-test", action="store_true", help="prove TTS→STT→wake→answer, no mic")
    ls.add_argument("--no-speak", action="store_true", help="print replies instead of speaking")
    ls.add_argument("--witness", action="store_true",
                    help="write an inspectable witness log of the exchange (implied by --once)")
    ls.set_defaults(func=cmd_listen)

    sy = sub.add_parser("say", help="Chirox speaks a line aloud (voice check)")
    sy.add_argument("text", help="the words to speak")
    sy.add_argument("--no-play", action="store_true", help="synthesize to a wav without playing")
    sy.set_defaults(func=cmd_say)

    me = sub.add_parser("memory", help="list sealed conversations the Master can recall")
    me.add_argument("--last", type=int, default=10, help="show only the last N (0 = all)")
    me.set_defaults(func=cmd_memory)

    fg = sub.add_parser("forget", help="withdraw one sealed event from recall (recorded, never silent)")
    fg.add_argument("seq", type=int, help="sequence number to withdraw (see: chirox memory)")
    fg.add_argument("--reason", required=True, help="why this memory is withdrawn")
    fg.set_defaults(func=cmd_forget)

    sub.add_parser("verify", help="check the Codex chain").set_defaults(func=cmd_verify)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
