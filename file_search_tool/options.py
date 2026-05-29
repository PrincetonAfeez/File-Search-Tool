"""CLI-to-library option helpers."""

from __future__ import annotations

from argparse import Namespace

from file_search_tool.errors import CLIError
from file_search_tool.dateparse import modified_after, modified_before, modified_within
from file_search_tool.dsl import compile_ast, parse_query
from file_search_tool.filters import (
    ContentPredicate,
    ExtensionPredicate,
    ModifiedTimePredicate,
    NamePredicate,
    PathPredicate,
    Predicate,
    SizePredicate,
    TypePredicate,
    combine_with_and,
)
from file_search_tool.models import CliDisplayOptions, SearchOptions
from file_search_tool.sizeparse import parse_size_expression
from file_search_tool.utils import split_csv_values


def split_extensions(value: str | None) -> list[str]:
    return split_csv_values(value)


def effective_content_case_sensitive(options: SearchOptions) -> bool:
    if options.content_case_sensitive is None:
        return options.case_sensitive
    return options.content_case_sensitive


def options_from_namespace(args: Namespace) -> tuple[SearchOptions, CliDisplayOptions]:
    if args.ignore_case and args.case_sensitive:
        raise CLIError("cannot use --ignore-case and --case-sensitive together")

    case_sensitive = True
    if args.ignore_case:
        case_sensitive = False
    if args.case_sensitive:
        case_sensitive = True

    content_case_sensitive = case_sensitive
    if args.content_ignore_case:
        content_case_sensitive = False

    if args.depth is not None and args.depth < 0:
        raise CLIError("--depth must be 0 or greater")
    if args.limit is not None and args.limit <= 0:
        raise CLIError("--limit must be greater than 0")
    if args.exclude and any(not pattern for pattern in args.exclude):
        raise CLIError("--exclude pattern cannot be empty")

    binary_policy = "error" if args.binary_error else "skip"

    search_options = SearchOptions(
        include_hidden=args.include_hidden,
        follow_symlinks=args.follow_symlinks,
        max_depth=args.depth,
        exclude_patterns=[pattern for pattern in args.exclude if pattern] if args.exclude else [],
        case_sensitive=case_sensitive,
        content_case_sensitive=content_case_sensitive,
        limit=args.limit,
        binary_policy=binary_policy,
    )
    display_options = CliDisplayOptions(
        sort_by=args.sort,
        output_format=args.output_format,
        show_summary=args.summary,
        verbose=args.verbose,
    )
    return search_options, display_options


def predicate_from_namespace(args: Namespace, options: SearchOptions) -> Predicate:
    predicates: list[Predicate] = []
    content_case_sensitive = effective_content_case_sensitive(options)

    if args.name is not None:
        predicates.append(NamePredicate(args.name, case_sensitive=options.case_sensitive))
    if args.regex_name is not None:
        predicates.append(NamePredicate(args.regex_name, regex=True, case_sensitive=options.case_sensitive))
    if args.path_pattern is not None:
        predicates.append(PathPredicate(args.path_pattern, case_sensitive=options.case_sensitive))

    if args.ext is not None:
        extensions = split_extensions(args.ext)
        if not extensions:
            raise CLIError("extension list cannot be empty")
        predicates.append(ExtensionPredicate(extensions, case_sensitive=options.case_sensitive))

    if args.entry_type:
        predicates.append(TypePredicate(args.entry_type))
    if args.size is not None:
        predicates.append(SizePredicate(parse_size_expression(args.size)))
    if args.modified_before is not None:
        predicates.append(ModifiedTimePredicate(modified_before(args.modified_before)))
    if args.modified_after is not None:
        predicates.append(ModifiedTimePredicate(modified_after(args.modified_after)))
    if args.modified_within is not None:
        predicates.append(ModifiedTimePredicate(modified_within(args.modified_within)))
    if args.contains is not None:
        predicates.append(
            ContentPredicate(
                args.contains,
                case_sensitive=content_case_sensitive,
                binary_policy=options.binary_policy,
            )
        )
    if args.contains_regex is not None:
        predicates.append(
            ContentPredicate(
                args.contains_regex,
                regex=True,
                case_sensitive=content_case_sensitive,
                binary_policy=options.binary_policy,
            )
        )
    if args.query is not None:
        predicates.append(
            compile_ast(
                parse_query(args.query),
                case_sensitive=options.case_sensitive,
                content_case_sensitive=content_case_sensitive,
                binary_policy=options.binary_policy,
            )
        )

    return combine_with_and(predicates)
