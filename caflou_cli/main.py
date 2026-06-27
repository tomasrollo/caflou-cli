import typer

from caflou_cli.commands import auth, comment, company, contact, document, masterdata, project, task, timesheet, transfer

app = typer.Typer(
    name="caflou",
    help="CLI tool for the Caflou project management API.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(auth.app, name="auth")
app.add_typer(comment.app, name="comment")
app.add_typer(masterdata.app, name="masterdata")
app.add_typer(company.app, name="company")
app.add_typer(contact.app, name="contact")
app.add_typer(document.app, name="document")
app.add_typer(project.app, name="project")
app.add_typer(task.app, name="task")
app.add_typer(timesheet.app, name="timesheet")
app.add_typer(transfer.app, name="transfer")
