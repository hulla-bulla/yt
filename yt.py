import click

@click.group()
def cli():
    pass

@cli.command()
def hello():
    click.echo("Hello World")

@cli.command()
@click.option('-n', '--name', type=str, help='Name to greet', default='World')
def hello2(name):
    click.echo(f'Hello {name}')