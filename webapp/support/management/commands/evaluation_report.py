"""Module 8: print the evaluation and safety report; exit 1 when the release is blocked."""

from django.core.management.base import BaseCommand, CommandError

from support.report import run_report, to_markdown


class Command(BaseCommand):
    help = "Run every offline evaluation and print the Markdown release report."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="Also write the report to this file.")

    def handle(self, *args, **options):
        report = run_report()
        text = to_markdown(report)
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as handle:
                handle.write(text)
        self.stdout.write(text)
        if report["verdict"] != "pass":
            raise CommandError("Release blocked: " + "; ".join(report["blocked"]))
