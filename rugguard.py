# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json

POSITIVE = ["team_identified", "audit_present", "source_verified", "active_development"]
RED_FLAGS = ["guaranteed_returns", "urgency_pressure", "anonymous_team"]
ORDER = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


def level_from(signals: dict) -> str:
    red = sum(1 for s in RED_FLAGS if signals[s] is True)
    yes = sum(1 for s in POSITIVE if signals[s] == "yes")
    if red >= 2:
        return "HIGH"
    if red == 1:
        return "MEDIUM" if yes >= 2 else "HIGH"
    if yes >= 3:
        return "LOW"
    if yes >= 1:
        return "MEDIUM"
    return "UNKNOWN"


class RugGuard(gl.Contract):
    reports: TreeMap[str, str]
    disputes: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def check(self, url: str, extra_url: str) -> str:
        url_copy = url
        extra_copy = extra_url
        checker = str(gl.message.sender_address)

        def analyze() -> str:
            text = gl.nondet.web.render(url_copy, mode="text")[:3500]
            if extra_copy:
                try:
                    text += "\n---\n" + gl.nondet.web.render(extra_copy, mode="text")[:3500]
                except Exception:
                    pass
            prompt = f"""
Extract factual signals about a crypto project from the text below.
Never guess. If the text gives no evidence, use "unknown" (never "no").

TEXT:
{text}

Return JSON with exactly these keys:
- team_identified, audit_present, source_verified, active_development:
  each "yes", "no" (explicitly absent) or "unknown"
- guaranteed_returns, urgency_pressure, anonymous_team:
  each true ONLY if the text explicitly shows it, else false
"""
            data = gl.nondet.exec_prompt(prompt, response_format="json")
            out = {}
            for s in POSITIVE:
                v = str(data.get(s, "unknown")).lower()
                out[s] = v if v in ("yes", "no", "unknown") else "unknown"
            for s in RED_FLAGS:
                out[s] = bool(data.get(s, False))
            return json.dumps({"signals": out, "page_chars": len(text)}, sort_keys=True)

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            mine = json.loads(analyze())["signals"]
            theirs = json.loads(leaders_res.calldata)["signals"]
            red_diff = sum(1 for s in RED_FLAGS if mine[s] != theirs[s])
            gap = abs(ORDER[level_from(mine)] - ORDER[level_from(theirs)])
            return red_diff <= 1 and gap <= 1

        raw = json.loads(gl.vm.run_nondet_unsafe(analyze, validator_fn))
        previous = json.loads(self.reports.get(url, "{}"))
        report = {
            "url": url,
            "extra_url": extra_url,
            "signals": raw["signals"],
            "page_chars": raw["page_chars"],
            "risk_level": level_from(raw["signals"]),
            "checked_by": checker,
            "check_count": previous.get("check_count", 0) + 1,
        }
        result = json.dumps(report, sort_keys=True)
        self.reports[url] = result
        return result

    @gl.public.write
    def dispute(self, url: str, reason: str) -> None:
        if url not in self.reports:
            raise gl.UserError("No report for this url")
        items = json.loads(self.disputes.get(url, "[]"))
        items.append({"by": str(gl.message.sender_address), "reason": reason[:300]})
        self.disputes[url] = json.dumps(items)

    @gl.public.view
    def get_report(self, url: str) -> str:
        return self.reports.get(url, "")

    @gl.public.view
    def get_disputes(self, url: str) -> str:
        return self.disputes.get(url, "[]")
