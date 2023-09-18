from collections.abc import Sequence

import discord
from discord.ext import commands

import breadcord
from breadcord.module import ModuleCog


def command_bullet_point(command: commands.Command, /) -> str:
    return (
        f"- {command.qualified_name}" + (
        f"\n  - {command.short_doc}" if command.short_doc else "")
    )


class HelpCommand(commands.MinimalHelpCommand):
    def __init__(self):
        super().__init__()

    async def send_pages(self):
        for page in self.paginator.pages:
            await self.get_destination().send(embed=discord.Embed(
                description=page,
                color=self.context.me.colour if self.context.me.colour.value else discord.Colour.blurple(),
            ))

    def add_bot_commands_formatting(self, cmds: Sequence[commands.Command], heading: str, /) -> None:
        if cmds:
            joined = "\n".join(command_bullet_point(cmd) for cmd in cmds)
            self.paginator.add_line(f"### {heading}")
            self.paginator.add_line(joined)

    def add_aliases_formatting(self, aliases: Sequence[str], /) -> None:
        self.paginator.add_line(
            f"### {self.aliases_heading}\n" + "\n".join(
                f"- {alias}"
                for alias in aliases
            )
        )
    def add_subcommand_formatting(self, command: commands.Command, /) -> None:
        self.paginator.add_line(command_bullet_point(command))

    async def send_cog_help(self, cog: commands.Cog, /) -> None:
        bot = self.context.bot
        if bot.description:
            self.paginator.add_line(bot.description)
        if note := self.get_opening_note():
            self.paginator.add_line(note)
        if cog.description:
            self.paginator.add_line(cog.description)

        filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
        if filtered:
            self.paginator.add_line(f'### {cog.qualified_name} {self.commands_heading}')
            for command in filtered:
                self.add_subcommand_formatting(command)

            if note := self.get_ending_note():
                self.paginator.add_line()
                self.paginator.add_line(note)

        await self.send_pages()

    def add_command_formatting(self, command: commands.Command, /) -> None:
        if command.description:
            self.paginator.add_line(command.description, empty=True)

        signature = self.get_command_signature(command)
        self.paginator.add_line(signature, empty=not command.aliases)

        if command.aliases:
            self.add_aliases_formatting(command.aliases)

        if command.help:
            try:
                self.paginator.add_line(command.help, empty=True)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
                self.paginator.add_line()


class BetterHelp(ModuleCog):
    def __init__(self, module_id: str) -> None:
        super().__init__(module_id)
        self.previous_help_command = self.bot.help_command

    def cog_load(self) -> None:
        self.previous_help_command = self.bot.help_command
        self.bot.help_command = HelpCommand()

    def cog_unload(self) -> None:
        self.bot.help_command = self.previous_help_command


async def setup(bot: breadcord.Bot):
    await bot.add_cog(BetterHelp("better_help_command"))
