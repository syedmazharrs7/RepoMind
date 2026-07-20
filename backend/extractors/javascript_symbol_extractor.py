import logging
from typing import List, Optional

import tree_sitter

from backend.extractors.base_symbol_extractor import (
    ASTNodeContext,
    BaseSymbolExtractor,
)
from backend.parse_result import ParseResult
from backend.symbol import Symbol, generate_symbol_id
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


class JavaScriptSymbolExtractor(BaseSymbolExtractor):
    """Symbol extractor specialized for JavaScript ASTs using Tree-sitter."""

    def _extract_language_symbols(
        self,
        parse_result: ParseResult,
        root_ctx: ASTNodeContext,
        module_symbol: Symbol,
        symbols_list: List[Symbol],
    ) -> None:
        """Single pass traversal of JavaScript AST."""
        self._traverse_js_node(
            ctx=root_ctx,
            parse_result=parse_result,
            parent_symbol=module_symbol,
            scope_qname=module_symbol.qualified_name,
            symbols_list=symbols_list,
            is_exported_context=False,
        )

    def _traverse_js_node(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        is_exported_context: bool = False,
    ) -> None:
        """Recursively walk JS AST nodes."""
        children = ctx.node.children
        for i, child in enumerate(children):
            c_ctx = ASTNodeContext(child, ctx.code_bytes)
            jsdoc = self._find_preceding_jsdoc(children, i, ctx.code_bytes)

            self._process_single_node(
                c_ctx=c_ctx,
                parse_result=parse_result,
                parent_symbol=parent_symbol,
                scope_qname=scope_qname,
                symbols_list=symbols_list,
                is_exported_context=is_exported_context,
                jsdoc=jsdoc,
            )

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
        """Polymorphic node dispatcher for JS AST nodes."""
        node_type = c_ctx.type

        if node_type == "export_statement":
            self._process_export_statement(
                c_ctx, parse_result, parent_symbol, scope_qname, symbols_list, jsdoc
            )
        elif node_type == "class_declaration":
            self._process_class_declaration(
                c_ctx, parse_result, parent_symbol, scope_qname, symbols_list, is_exported_context, jsdoc
            )
        elif node_type == "function_declaration":
            self._process_function_declaration(
                c_ctx, parse_result, parent_symbol, scope_qname, symbols_list, is_exported_context, jsdoc
            )
        elif node_type in ("lexical_declaration", "variable_declaration"):
            self._process_variable_declaration(
                c_ctx, parse_result, parent_symbol, scope_qname, symbols_list, is_exported_context, jsdoc
            )
        elif node_type == "method_definition":
            self._process_method_definition(
                c_ctx, parse_result, parent_symbol, scope_qname, symbols_list, jsdoc
            )
        elif node_type == "import_statement":
            self._process_import_statement(c_ctx, parse_result, parent_symbol, scope_qname, symbols_list)

    def _process_export_statement(
        self,
        export_ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        jsdoc: Optional[str],
    ) -> None:
        """Process export statement wrapping declarations."""
        declaration = export_ctx.child_by_field_name("declaration")
        if declaration:
            self._process_single_node(
                c_ctx=declaration,
                parse_result=parse_result,
                parent_symbol=parent_symbol,
                scope_qname=scope_qname,
                symbols_list=symbols_list,
                is_exported_context=True,
                jsdoc=jsdoc,
            )
        else:
            for child in export_ctx.node.children:
                c_ctx = ASTNodeContext(child, export_ctx.code_bytes)
                if c_ctx.type not in ("export", ";"):
                    self._process_single_node(
                        c_ctx=c_ctx,
                        parse_result=parse_result,
                        parent_symbol=parent_symbol,
                        scope_qname=scope_qname,
                        symbols_list=symbols_list,
                        is_exported_context=True,
                        jsdoc=jsdoc,
                    )

    def _process_class_declaration(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        is_exported: bool,
        jsdoc: Optional[str],
    ) -> None:
        """Extract JavaScript class symbol."""
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

        class_symbol = Symbol(
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
            signature=f"class {name}",
            docstring=jsdoc,
            decorators=(),
            visibility="exported" if is_exported else "public",
            is_async=False,
            is_exported=is_exported,
        )
        symbols_list.append(class_symbol)

        body_node = ctx.child_by_field_name("body")
        if body_node:
            self._traverse_js_node(
                ctx=body_node,
                parse_result=parse_result,
                parent_symbol=class_symbol,
                scope_qname=qualified_name,
                symbols_list=symbols_list,
                is_exported_context=False,
            )

    def _process_function_declaration(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        is_exported: bool,
        jsdoc: Optional[str],
    ) -> None:
        """Extract JS function declaration."""
        name_node = ctx.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text
        qualified_name = f"{scope_qname}.{name}"
        is_async = any(c.type == "async" for c in ctx.node.children) or ctx.text.startswith("async ")

        params_node = ctx.child_by_field_name("parameters")
        params_str = params_node.text if params_node else "()"
        async_prefix = "async " if is_async else ""
        signature = f"{async_prefix}function {name}{params_str}"

        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=file_path,
            qualified_name=qualified_name,
            kind=SymbolKind.FUNCTION,
        )

        func_symbol = Symbol(
            id=symbol_id,
            name=name,
            qualified_name=qualified_name,
            kind=SymbolKind.FUNCTION,
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
            visibility="exported" if is_exported else "public",
            is_async=is_async,
            is_exported=is_exported,
        )
        symbols_list.append(func_symbol)

        if params_node:
            self._extract_js_parameters(params_node, parse_result, func_symbol, qualified_name, symbols_list)

        body_node = ctx.child_by_field_name("body")
        if body_node:
            self._traverse_js_node(
                ctx=body_node,
                parse_result=parse_result,
                parent_symbol=func_symbol,
                scope_qname=qualified_name,
                symbols_list=symbols_list,
                is_exported_context=False,
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
        """Extract JavaScript method / constructor symbol."""
        name_node = ctx.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text
        qualified_name = f"{scope_qname}.{name}"
        is_async = any(c.type == "async" for c in ctx.node.children) or ctx.text.startswith("async ")

        kind = SymbolKind.CONSTRUCTOR if name == "constructor" else SymbolKind.METHOD
        visibility = "private" if name.startswith("#") else "public"

        params_node = ctx.child_by_field_name("parameters")
        params_str = params_node.text if params_node else "()"
        async_prefix = "async " if is_async else ""
        signature = f"{async_prefix}{name}{params_str}"

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

    def _process_variable_declaration(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        is_exported: bool,
        jsdoc: Optional[str],
    ) -> None:
        """Extract lexical declaration (const / let / var)."""
        is_const = ctx.text.startswith("const ")
        kind_default = SymbolKind.CONSTANT if is_const else SymbolKind.VARIABLE

        declarators = ctx.children_by_type("variable_declarator")
        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        for decl in declarators:
            name_node = decl.child_by_field_name("name")
            value_node = decl.child_by_field_name("value")
            if not name_node:
                continue

            name = name_node.text
            qualified_name = f"{scope_qname}.{name}"

            is_arrow_or_func = value_node is not None and value_node.type in ("arrow_function", "function_expression")
            kind = SymbolKind.FUNCTION if is_arrow_or_func else kind_default

            is_async = False
            signature = ctx.text
            if is_arrow_or_func and value_node:
                is_async = any(c.type == "async" for c in value_node.node.children) or value_node.text.startswith("async")
                async_prefix = "async " if is_async else ""
                params_node = value_node.child_by_field_name("parameters")
                params_str = params_node.text if params_node else "()"
                signature = f"{async_prefix}const {name} = {params_str} => ..."

            symbol_id = generate_symbol_id(
                language=lang,
                file_path=file_path,
                qualified_name=qualified_name,
                kind=kind,
            )

            var_symbol = Symbol(
                id=symbol_id,
                name=name,
                qualified_name=qualified_name,
                kind=kind,
                language=lang,
                file_path=file_path,
                start_line=decl.start_line,
                end_line=decl.end_line,
                start_column=decl.start_column,
                end_column=decl.end_column,
                parent_symbol=parent_symbol.id,
                signature=signature,
                docstring=jsdoc,
                decorators=(),
                visibility="exported" if is_exported else "public",
                is_async=is_async,
                is_exported=is_exported,
            )
            symbols_list.append(var_symbol)

            if is_arrow_or_func and value_node:
                body_node = value_node.child_by_field_name("body")
                if body_node and body_node.type == "statement_block":
                    self._traverse_js_node(
                        ctx=body_node,
                        parse_result=parse_result,
                        parent_symbol=var_symbol,
                        scope_qname=qualified_name,
                        symbols_list=symbols_list,
                        is_exported_context=False,
                    )

    def _extract_js_parameters(
        self,
        params_ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
    ) -> None:
        """Extract parameter symbols."""
        for param in params_ctx.node.children:
            p_ctx = ASTNodeContext(param, params_ctx.code_bytes)
            if p_ctx.type in ("identifier", "formal_parameter", "assignment_pattern", "rest_pattern"):
                p_name = p_ctx.text.split("=")[0].split(":")[0].strip()
                if not p_name or p_name in ("(", ")", ","):
                    continue

                param_qname = f"{scope_qname}.{p_name}"
                file_path = parse_result.source_file.relative_path
                lang = parse_result.source_file.language

                symbol_id = generate_symbol_id(
                    language=lang,
                    file_path=file_path,
                    qualified_name=param_qname,
                    kind=SymbolKind.PARAMETER,
                )

                symbols_list.append(
                    Symbol(
                        id=symbol_id,
                        name=p_name,
                        qualified_name=param_qname,
                        kind=SymbolKind.PARAMETER,
                        language=lang,
                        file_path=file_path,
                        start_line=p_ctx.start_line,
                        end_line=p_ctx.end_line,
                        start_column=p_ctx.start_column,
                        end_column=p_ctx.end_column,
                        parent_symbol=parent_symbol.id,
                        signature=p_ctx.text,
                        docstring=None,
                        decorators=(),
                        visibility="public",
                        is_async=False,
                        is_exported=False,
                    )
                )

    def _process_import_statement(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
    ) -> None:
        """Extract JS import statement."""
        import_text = ctx.text.strip()
        if not import_text:
            return

        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language
        qname = f"{scope_qname}.import_{ctx.start_line}_{ctx.start_column}"

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=file_path,
            qualified_name=qname,
            kind=SymbolKind.IMPORT,
        )

        symbols_list.append(
            Symbol(
                id=symbol_id,
                name=import_text,
                qualified_name=qname,
                kind=SymbolKind.IMPORT,
                language=lang,
                file_path=file_path,
                start_line=ctx.start_line,
                end_line=ctx.end_line,
                start_column=ctx.start_column,
                end_column=ctx.end_column,
                parent_symbol=parent_symbol.id,
                signature=import_text,
                docstring=None,
                decorators=(),
                visibility="public",
                is_async=False,
                is_exported=False,
            )
        )

    def _find_preceding_jsdoc(
        self, children: List[tree_sitter.Node], target_index: int, code_bytes: bytes
    ) -> Optional[str]:
        """Find JSDoc comment preceding node at target_index."""
        if target_index > 0:
            prev_child = children[target_index - 1]
            if prev_child.type == "comment":
                c_ctx = ASTNodeContext(prev_child, code_bytes)
                text = c_ctx.text.strip()
                if text.startswith("/**") and text.endswith("*/"):
                    lines = text[3:-2].strip().splitlines()
                    clean_lines = [line.strip().lstrip("*").strip() for line in lines]
                    return "\n".join(clean_lines).strip()
        return None
