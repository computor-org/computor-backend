import time
import click
from alive_progress import alive_bar

@click.command()
def experiment_1():

    with alive_bar(title="Test",monitor=None, stats=None,spinner='twirls') as bar:
      for i in range(30000):
        time.sleep(0.1)
        bar()
        bar.text('[scheduled]')