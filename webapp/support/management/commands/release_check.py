"""Module 9: readiness checks, Django's deploy checks and the Module 8 report; exit 1 when any fails."""

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, SystemCheckError

from support.ops import readiness
from support.report import run_report


class Command(BaseCommand):
    help = "Check that this configuration is ready to deploy and that the release report passes."

    def handle(self, *args, **options):
        failed = []
        result = readiness()
        for c in result["checks"]:
            self.stdout.write(f"{'pass' if c['ok'] else 'FAIL'}  {c['key']:<20} {c['label']} ({c['detail']})")
        if not result["ready"]:
            failed.append("readiness: " + ", ".join(result["failing"]))
        try:
            call_command("check", deploy=True, fail_level="WARNING", stdout=self.stdout, stderr=self.stderr)
        except SystemCheckError as exc:
            self.stderr.write(str(exc))
            failed.append("Django deploy checks")
        try:
            report = run_report()
        except (OSError, ValueError, KeyError) as exc:  # a broken data file is a failed check, not a crash
            self.stdout.write(f"Evaluation report: could not run ({exc})")
            failed.append("report could not run")
        else:
            self.stdout.write(f"Evaluation report: {report['verdict']}")
            if report["blocked"]:
                failed.append("report blocked by " + "; ".join(report["blocked"]))
        if failed:
            raise CommandError("Not ready to deploy: " + " | ".join(failed))
        self.stdout.write("Ready to deploy.")
