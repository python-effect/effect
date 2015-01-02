from effect import Effect

from .github_api import get_orgs_repos
from .readline_intent import ReadLine


def main_effect():
    """
    Request a username from the keyboard, and look up all repos in all of
    that user's organizations.

    :return: an Effect resulting in a list of repositories.
    """
    intent = ReadLine("Enter Github Username> ")
    read_eff = Effect(intent)
    org_repos_eff = read_eff.on(success=get_orgs_repos)
    return org_repos_eff
