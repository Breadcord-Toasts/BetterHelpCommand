import itertools
from collections.abc import Sequence
from typing import Any, Mapping

import discord
from discord.ext import commands

import breadcord
from breadcord.module import ModuleCog


def command_bullet_point(command: commands.Command, /) -> str:
    short_doc = command.short_doc
    if not short_doc and command.description:
        short_doc = command.description.split("\n", 1)[0]

    short_doc_limit = 140
    if len(short_doc) > short_doc_limit:
        short_doc = short_doc[:short_doc_limit-3] + "..."

    return (
        f"- {command.qualified_name}"
        + (f"\n  - {short_doc}" if short_doc else "")
    )


class HelpCommand(commands.MinimalHelpCommand):
    def __init__(self) -> None:
        super().__init__()
        self.no_category = "Core Commands"

    async def send_pages(self) -> None:
        for page in self.paginator.pages:
            await self.get_destination().send(embed=discord.Embed(
                description=page,
                color=self.context.me.colour if self.context.me.colour.value else discord.Colour.blurple(),
            ))

    def add_aliases_formatting(self, aliases: Sequence[str], /) -> None:
        self.paginator.add_line(
            f"### Aliases\n" + "\n".join(
                f"- {alias}"
                for alias in aliases
            )
        )

    def add_subcommand_formatting(self, command: commands.Command, /) -> None:
        self.paginator.add_line(command_bullet_point(command))

    def add_bot_commands_formatting(self, cmds: Sequence[commands.Command], heading: str, /) -> None:
        if not cmds:
            return
        self.paginator.add_line(f"### {heading}")
        self.paginator.add_line("\n".join(command_bullet_point(cmd) for cmd in cmds))

    async def send_bot_help(
        self,
        mapping: Mapping[commands.Cog | None, list[commands.Command[Any, ..., Any]]], /
    ) -> None:
        if self.context.bot.description:
            self.paginator.add_line(self.context.bot.description, empty=True)

        note = self.get_opening_note()
        if note:
            self.paginator.add_line(note, empty=True)

        def get_category(command: commands.Command[Any, ..., Any], *, no_category: str = self.no_category) -> str:
            cog = command.cog
            return cog.qualified_name if cog is not None else no_category

        filtered = await self.filter_commands(self.context.bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        for category, cmds in to_iterate:
            cmds = sorted(cmds, key=lambda c: c.name) if self.sort_commands else list(cmds)
            self.add_bot_commands_formatting(cmds, category)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

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
            self.paginator.add_line(f'### {self.commands_heading}')
            for command in filtered:
                self.add_subcommand_formatting(command)

            if note := self.get_ending_note():
                self.paginator.add_line()
                self.paginator.add_line(note)

        await self.send_pages()

    async def send_group_help(self, group: commands.Group[Any, ..., Any], /) -> None:
        self.add_command_formatting(group)  # type: ignore

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        if filtered:
            note = self.get_opening_note()
            if note:
                self.paginator.add_line(note, empty=True)

            self.paginator.add_line(f'### Commands')
            for command in filtered:
                self.add_subcommand_formatting(command)

            note = self.get_ending_note()
            if note:
                self.paginator.add_line()
                self.paginator.add_line(note)

        await self.send_pages()

    async def send_error_message(self, error: str, /) -> None:
        destination = self.get_destination()
        await destination.send(embed=discord.Embed(
            description=error,
            color=discord.Colour.red(),
        ))

    def add_command_formatting(self, command: commands.Command[Any, ..., Any], /) -> None:
        if command.description:
            self.paginator.add_line(
                "\n".join(f"> {line}" for line in command.description.splitlines()),
                empty=True
            )

        if command.help:
            try:
                self.paginator.add_line(command.help, empty=True)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
                self.paginator.add_line()

        signature = self.get_command_signature(command)
        self.paginator.add_line(f"**Usage:** `{signature}`", empty=not command.aliases)

        if command.aliases:
            self.add_aliases_formatting(command.aliases)

        for param in command.params.values():
            if not param.description:
                continue
            self.paginator.add_line("\n".join((
                f"### {param.name}",
                f"- {param.kind.description}",
                f"{param.description}",
            )))

    def command_not_found(self, string: str, /) -> str:
        return (
            f"{super().command_not_found(string)}\n"
            f"Ensure that it is spelled and capitalized correctly."
        )

    def get_opening_note(self) -> str:
        return ""


class BetterHelp(ModuleCog):
    def __init__(self, module_id: str) -> None:
        super().__init__(module_id)
        self.previous_help_command = self.bot.help_command

    async def cog_load(self) -> None:
        self.previous_help_command = self.bot.help_command
        self.bot.help_command = HelpCommand()

    async def cog_unload(self) -> None:
        self.bot.help_command = self.previous_help_command


async def setup(bot: breadcord.Bot):
    await bot.add_cog(BetterHelp("better_help_command"))
