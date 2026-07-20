import logging
from typing import List, Optional

from backend.extractors.base_symbol_extractor import ASTNodeContext
from backend.extractors.javascript_symbol_extractor import JavaScriptSymbolExtractor
from backend.parse_result import ParseResult
from backend.symbol import Symbol, generate_symbol_id
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


class TypeScriptSymbolExtractor(JavaScriptSymbolExtractor):
    """Symbol extractor specialized for TypeScript ASTs, extending JS extractor with type & accessibility features."""

    def _process_single_node(
        self,
        c_ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        is_exported_context: bool = False,
        jsdoc: Optional[str] = None,
    ) -> None:
        """Override JS node dispatcher to include TS interface, enum, and type alias nodes."""
        node_type = c_ctx.type

        if node_type == "interface_declaration":
            self._process_ts_interface(c_ctx, parse_result, parent_symbol, scope_qname, symbols_list, is_exported_context, jsdoc)
        elif node_type == "enum_declaration":
            self._process_ts_enum(c_ctx, parse_result, parent_symbol, scope_qname, symbols_list, is_exported_context, jsdoc)
        elif node_type == "type_alias_declaration":
            self._process_ts_type_alias(c_ctx, parse_result, parent_symbol, scope_qname, symbols_list, is_exported_context, jsdoc)
        else:
            super()._process_single_node(
                c_ctx=c_ctx,
                parse_result=parse_result,
                parent_symbol=parent_symbol,
                scope_qname=scope_qname,
                symbols_list=symbols_list,
                is_exported_context=is_exported_context,
                jsdoc=jsdoc,
            )

    def _process_method_definition(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        jsdoc: Optional[str],
    ) -> None:
        """Extract TypeScript method definition with accessibility modifiers (public, private, protected)."""
        visibility = "public"
        for child in ctx.node.children:
            if child.type in ("accessibility_modifier", "public", "private", "protected"):
                visibility = child.text.decode("utf-8", errors="replace").strip()
                break

        name_node = ctx.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text
        qualified_name = f"{scope_qname}.{name}"
        is_async = any(c.type == "async" for c in ctx.node.children) or ctx.text.startswith("async ")

        kind = SymbolKind.CONSTRUCTOR if name == "constructor" else SymbolKind.METHOD

        params_node = ctx.child_by_field_name("parameters")
        params_str = params_node.text if params_node else "()"
        return_type_node = ctx.child_by_field_name("return_type")
        ret_str = f": {return_type_node.text}" if return_type_node else ""
        async_prefix = "async " if is_async else ""
        signature = f"{visibility} {async_prefix}{name}{params_str}{ret_str}".strip()

        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=file_path,
            qualified_name=qualified_name,
            kind=kind,
        )

        method_symbol = Symbol(
            id=symbol_id,
            name=name,
            qualified_name=qualified_name,
            kind=kind,
            language=lang,
            file_path=file_path,
            start_line=ctx.start_line,
            end_line=ctx.end_line,
            start_column=ctx.start_column,
            end_column=ctx.end_column,
            parent_symbol=parent_symbol.id,
            signature=signature,
            docstring=jsdoc,
            decorators=(),
            visibility=visibility,
            is_async=is_async,
            is_exported=False,
        )
        symbols_list.append(method_symbol)

        if params_node:
            self._extract_js_parameters(params_node, parse_result, method_symbol, qualified_name, symbols_list)

        body_node = ctx.child_by_field_name("body")
        if body_node:
            self._traverse_js_node(
                ctx=body_node,
                parse_result=parse_result,
                parent_symbol=method_symbol,
                scope_qname=qualified_name,
                symbols_list=symbols_list,
                is_exported_context=False,
            )

    def _process_ts_interface(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        is_exported: bool,
        jsdoc: Optional[str],
    ) -> None:
        """Extract TS interface as CLASS symbol."""
        name_node = ctx.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text
        qualified_name = f"{scope_qname}.{name}"
        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=file_path,
            qualified_name=qualified_name,
            kind=SymbolKind.CLASS,
        )

        symbols_list.append(
            Symbol(
                id=symbol_id,
                name=name,
                qualified_name=qualified_name,
                kind=SymbolKind.CLASS,
                language=lang,
                file_path=file_path,
                start_line=ctx.start_line,
                end_line=ctx.end_line,
                start_column=ctx.start_column,
                end_column=ctx.end_column,
                parent_symbol=parent_symbol.id,
                signature=f"interface {name}",
                docstring=jsdoc,
                decorators=(),
                visibility="exported" if is_exported else "public",
                is_async=False,
                is_exported=is_exported,
            )
        )

    def _process_ts_enum(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        is_exported: bool,
        jsdoc: Optional[str],
    ) -> None:
        """Extract TS enum as CLASS symbol."""
        name_node = ctx.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text
        qualified_name = f"{scope_qname}.{name}"
        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=file_path,
            qualified_name=qualified_name,
            kind=SymbolKind.CLASS,
        )

        symbols_list.append(
            Symbol(
                id=symbol_id,
                name=name,
                qualified_name=qualified_name,
                kind=SymbolKind.CLASS,
                language=lang,
                file_path=file_path,
                start_line=ctx.start_line,
                end_line=ctx.end_line,
                start_column=ctx.start_column,
                end_column=ctx.end_column,
                parent_symbol=parent_symbol.id,
                signature=f"enum {name}",
                docstring=jsdoc,
                decorators=(),
                visibility="exported" if is_exported else "public",
                is_async=False,
                is_exported=is_exported,
            )
        )

    def _process_ts_type_alias(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        is_exported: bool,
        jsdoc: Optional[str],
    ) -> None:
        """Extract TS type alias as VARIABLE symbol."""
        name_node = ctx.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text
        qualified_name = f"{scope_qname}.{name}"
        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=file_path,
            qualified_name=qualified_name,
            kind=SymbolKind.VARIABLE,
        )

        symbols_list.append(
            Symbol(
                id=symbol_id,
                name=name,
                qualified_name=qualified_name,
                kind=SymbolKind.VARIABLE,
                language=lang,
                file_path=file_path,
                start_line=ctx.start_line,
                end_line=ctx.end_line,
                start_column=ctx.start_column,
                end_column=ctx.end_column,
                parent_symbol=parent_symbol.id,
                signature=f"type {name}",
                docstring=jsdoc,
                decorators=(),
                visibility="exported" if is_exported else "public",
                is_async=False,
                is_exported=is_exported,
            )
        )
