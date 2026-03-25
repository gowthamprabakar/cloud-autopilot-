"""
Email templates — simple Python f-string HTML templates.
All templates return (subject, html_body, text_body) tuples.
"""

_BASE_STYLE = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f8fafc; margin: 0; padding: 20px; }
.card { background: white; border-radius: 8px; padding: 24px;
        max-width: 560px; margin: 0 auto; border: 1px solid #e2e8f0; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
         font-size: 12px; font-weight: 600; }
.critical { background: #fee2e2; color: #991b1b; }
.high     { background: #ffedd5; color: #9a3412; }
.medium   { background: #fef9c3; color: #854d0e; }
.btn { display: inline-block; padding: 10px 20px; background: #2563eb;
       color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }
.footer { margin-top: 24px; font-size: 12px; color: #94a3b8; }
"""


def finding_assigned_email(
    assignee_name: str,
    finding_title: str,
    finding_severity: str,
    assigned_by: str,
    due_date: str | None,
    note: str | None,
    finding_url: str,
) -> tuple[str, str, str]:
    subject = f"Finding assigned to you: {finding_title[:60]}"
    due_str = f"<p><strong>Due:</strong> {due_date}</p>" if due_date else ""
    note_str = f"<p><strong>Note:</strong> {note}</p>" if note else ""
    html = f"""<!DOCTYPE html><html><head><style>{_BASE_STYLE}</style></head><body>
<div class="card">
  <h2 style="margin-top:0">Finding Assigned to You</h2>
  <p>Hi {assignee_name},</p>
  <p><strong>{assigned_by}</strong> has assigned a finding to you for remediation.</p>
  <p><strong>Finding:</strong> {finding_title}<br>
     <strong>Severity:</strong> <span class="badge {finding_severity.lower()}">{finding_severity.upper()}</span>
  </p>
  {due_str}{note_str}
  <p><a href="{finding_url}" class="btn">View Finding</a></p>
  <div class="footer">Cloud Posture Copilot — Security findings management</div>
</div></body></html>"""
    text = f"Finding assigned to you: {finding_title}\nSeverity: {finding_severity}\nAssigned by: {assigned_by}\n{f'Due: {due_date}' if due_date else ''}\n{f'Note: {note}' if note else ''}\nView: {finding_url}"
    return subject, html, text


def sla_breach_email(
    user_name: str,
    findings: list[dict],  # list of {title, severity, days_overdue, url}
    workspace_name: str,
) -> tuple[str, str, str]:
    count = len(findings)
    subject = f"SLA Breach Alert: {count} finding{'s' if count > 1 else ''} overdue in {workspace_name}"
    rows = ""
    for f in findings[:10]:  # cap at 10
        rows += f"""<tr>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0">
            <a href="{f['url']}">{f['title'][:60]}</a>
          </td>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0">
            <span class="badge {f['severity'].lower()}">{f['severity'].upper()}</span>
          </td>
          <td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#dc2626">
            {f['days_overdue']} days overdue
          </td>
        </tr>"""
    html = f"""<!DOCTYPE html><html><head><style>{_BASE_STYLE}</style></head><body>
<div class="card">
  <h2 style="margin-top:0;color:#dc2626">&#9888; SLA Breach Alert</h2>
  <p>Hi {user_name}, <strong>{count}</strong> finding{'s' if count > 1 else ''} in <strong>{workspace_name}</strong> {'have' if count > 1 else 'has'} breached their SLA deadline.</p>
  <table style="width:100%;border-collapse:collapse">
    <tr style="background:#f8fafc"><th style="padding:8px;text-align:left">Finding</th><th style="padding:8px;text-align:left">Severity</th><th style="padding:8px;text-align:left">Status</th></tr>
    {rows}
  </table>
  <p style="margin-top:16px"><a href="/dashboard/remediation" class="btn">View SLA Dashboard</a></p>
  <div class="footer">Cloud Posture Copilot</div>
</div></body></html>"""
    text = f"SLA Breach Alert: {count} findings overdue in {workspace_name}\n" + "\n".join(f"- {f['title']} ({f['severity']}, {f['days_overdue']}d overdue)" for f in findings[:10])
    return subject, html, text


def user_invited_email(
    invitee_name: str,
    inviter_name: str,
    workspace_name: str,
    login_url: str,
    temporary_password: str,
) -> tuple[str, str, str]:
    subject = f"You've been invited to {workspace_name} on Cloud Posture Copilot"
    html = f"""<!DOCTYPE html><html><head><style>{_BASE_STYLE}</style></head><body>
<div class="card">
  <h2 style="margin-top:0">You're invited!</h2>
  <p>Hi {invitee_name},</p>
  <p><strong>{inviter_name}</strong> has invited you to join <strong>{workspace_name}</strong> on Cloud Posture Copilot.</p>
  <p><strong>Your login details:</strong><br>
     Email: (your email address)<br>
     Temporary password: <code style="background:#f1f5f9;padding:2px 6px;border-radius:4px">{temporary_password}</code>
  </p>
  <p>Please change your password after first login.</p>
  <p><a href="{login_url}" class="btn">Accept Invitation</a></p>
  <div class="footer">Cloud Posture Copilot — You received this because you were invited by {inviter_name}</div>
</div></body></html>"""
    text = f"You've been invited to {workspace_name}.\nInvited by: {inviter_name}\nLogin: {login_url}\nTemporary password: {temporary_password}\nPlease change your password after login."
    return subject, html, text


def digest_email(
    workspace_name: str,
    total_open: int,
    critical: int,
    high: int,
    medium: int,
    low: int,
    resolved_this_week: int,
    top_findings: list[dict],  # list of {title, severity, account}
) -> tuple[str, str, str]:
    """Executive digest email for scheduled reports."""
    subject = f"Security Digest — {workspace_name}"
    rows = ""
    for f in top_findings[:5]:
        rows += f'<li>{f["title"][:60]} <span class="badge {f["severity"].lower()}">{f["severity"].upper()}</span> — {f.get("account", "")}</li>'
    html = f"""<!DOCTYPE html><html><head><style>{_BASE_STYLE}</style></head><body>
<div class="card">
  <h2 style="margin-top:0">Security Digest</h2>
  <p>Here is your security summary for <strong>{workspace_name}</strong>.</p>
  <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
    <tr>
      <td style="padding:12px;background:#fef2f2;border-radius:6px;text-align:center"><strong style="font-size:24px;color:#dc2626">{critical}</strong><br><small>Critical</small></td>
      <td style="width:8px"></td>
      <td style="padding:12px;background:#fff7ed;border-radius:6px;text-align:center"><strong style="font-size:24px;color:#ea580c">{high}</strong><br><small>High</small></td>
      <td style="width:8px"></td>
      <td style="padding:12px;background:#fef9c3;border-radius:6px;text-align:center"><strong style="font-size:24px;color:#854d0e">{medium}</strong><br><small>Medium</small></td>
      <td style="width:8px"></td>
      <td style="padding:12px;background:#f0fdf4;border-radius:6px;text-align:center"><strong style="font-size:24px;color:#16a34a">{resolved_this_week}</strong><br><small>Resolved (7d)</small></td>
    </tr>
  </table>
  <p><strong>Total Open:</strong> {total_open} &nbsp;|&nbsp; <strong>Low:</strong> {low}</p>
  {'<h3>Top Findings</h3><ul>' + rows + '</ul>' if top_findings else ''}
  <div class="footer">Cloud Posture Copilot — scheduled digest</div>
</div></body></html>"""
    text = f"Security Digest for {workspace_name}\nCritical: {critical} | High: {high} | Medium: {medium} | Low: {low}\nResolved this week: {resolved_this_week}\nTotal open: {total_open}"
    return subject, html, text


def weekly_digest_email(
    user_name: str,
    workspace_name: str,
    new_findings: int,
    resolved_findings: int,
    critical_open: int,
    sla_breached: int,
    top_findings: list[dict],  # list of {title, severity, url}
    report_url: str,
) -> tuple[str, str, str]:
    subject = f"Weekly Security Digest — {workspace_name}"
    rows = ""
    for f in top_findings[:5]:
        rows += f'<li><a href="{f["url"]}">{f["title"][:60]}</a> <span class="badge {f["severity"].lower()}">{f["severity"].upper()}</span></li>'
    html = f"""<!DOCTYPE html><html><head><style>{_BASE_STYLE}</style></head><body>
<div class="card">
  <h2 style="margin-top:0">Weekly Security Digest</h2>
  <p>Hi {user_name}, here's your weekly summary for <strong>{workspace_name}</strong>.</p>
  <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
    <tr><td style="padding:12px;background:#fef2f2;border-radius:6px;text-align:center"><strong style="font-size:24px;color:#dc2626">{critical_open}</strong><br><small>Critical Open</small></td>
        <td style="width:8px"></td>
        <td style="padding:12px;background:#fff7ed;border-radius:6px;text-align:center"><strong style="font-size:24px;color:#ea580c">{sla_breached}</strong><br><small>SLA Breached</small></td>
        <td style="width:8px"></td>
        <td style="padding:12px;background:#f0fdf4;border-radius:6px;text-align:center"><strong style="font-size:24px;color:#16a34a">{resolved_findings}</strong><br><small>Resolved</small></td></tr>
  </table>
  <p><strong>New this week:</strong> {new_findings} findings &nbsp;|&nbsp; <strong>Resolved:</strong> {resolved_findings}</p>
  {'<h3>Top Findings</h3><ul>' + rows + '</ul>' if top_findings else ''}
  <p><a href="{report_url}" class="btn">View Full Report</a></p>
  <div class="footer">Cloud Posture Copilot weekly digest</div>
</div></body></html>"""
    text = f"Weekly Digest for {workspace_name}\nCritical Open: {critical_open} | SLA Breached: {sla_breached} | Resolved: {resolved_findings}\nNew: {new_findings}"
    return subject, html, text
