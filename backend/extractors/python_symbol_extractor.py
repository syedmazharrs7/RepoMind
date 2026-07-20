import logging
from typing import List, Optional, Tuple

from backend.extractors.base_symbol_extractor import (
    ASTNodeContext,
    BaseSymbolExtractor,
)
from backend.parse_result import ParseResult
from backend.symbol import Symbol, generate_symbol_id
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


class PythonSymbolExtractor(BaseSymbolExtractor):
    """Symbol extractor specialized for Python ASTs using Tree-sitter."""

    def _extract_language_symbols(
        self,
        parse_result: ParseResult,
        root_ctx: ASTNodeContext,
        module_symbol: Symbol,
        symbols_list: List[Symbol],
    ) -> None:
        """Single-pass traversal of Python AST."""
        mod_docstring = self._extract_docstring_from_block(root_ctx)
        if mod_docstring and symbols_list and symbols_list[0].kind == SymbolKind.MODULE:
            symbols_list[0] = Symbol(
                id=module_symbol.id,
                name=module_symbol.name,
                qualified_name=module_symbol.qualified_name,
                kind=module_symbol.kind,
                language=module_symbol.language,
                file_path=module_symbol.file_path,
                start_line=module_symbol.start_line,
                end_line=module_symbol.end_line,
                start_column=module_symbol.start_column,
                end_column=module_symbol.end_column,
                parent_symbol=module_symbol.parent_symbol,
                signature=module_symbol.signature,
                docstring=mod_docstring,
                decorators=module_symbol.decorators,
                visibility=module_symbol.visibility,
                is_async=module_symbol.is_async,
                is_exported=module_symbol.is_exported,
            )
            module_symbol = symbols_list[0]

        self._traverse_node(
            ctx=root_ctx,
            parse_result=parse_result,
            parent_symbol=module_symbol,
            scope_qname=module_symbol.qualified_name,
            symbols_list=symbols_list,
            decorators=(),
        )

    def _traverse_node(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        decorators: Tuple[str, ...] = (),
    ) -> None:
        """Traverse AST nodes in single pass."""
        for child in ctx.node.children:
            child_ctx = ASTNodeContext(child, ctx.code_bytes)
            node_type = child_ctx.type

            if node_type == "decorated_definition":
                decs, def_node = self._unpack_decorated_definition(child_ctx)
                if def_node:
                    self._process_definition(
                        def_node,
                        parse_result,
                        parent_symbol,
                        scope_qname,
                        symbols_list,
                        decorators=decs,
                    )
            elif node_type in ("class_definition", "function_definition"):
                self._process_definition(
                    child_ctx,
                    parse_result,
                    parent_symbol,
                    scope_qname,
                    symbols_list,
                    decorators=decorators,
                )
            elif node_type in ("import_statement", "import_from_statement"):
                self._process_import(child_ctx, parse_result, parent_symbol, scope_qname, symbols_list)
            elif node_type in ("expression_statement", "assignment"):
                self._process_assignment_or_expr(child_ctx, parse_result, parent_symbol, scope_qname, symbols_list)

    def _unpack_decorated_definition(
        self, decorated_ctx: ASTNodeContext
    ) -> Tuple[Tuple[str, ...], Optional[ASTNodeContext]]:
        """Extract decorator names and target definition from decorated_definition."""
        decorators: List[str] = []
        target_def: Optional[ASTNodeContext] = None

        for child in decorated_ctx.node.children:
            c_ctx = ASTNodeContext(child, decorated_ctx.code_bytes)
            if c_ctx.type == "decorator":
                dec_text = c_ctx.text.strip()
                if dec_text:
                    decorators.append(dec_text)
            elif c_ctx.type in ("class_definition", "function_definition"):
                target_def = c_ctx

        return tuple(decorators), target_def

    def _process_definition(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        decorators: Tuple[str, ...] = (),
    ) -> None:
        """Process class or function definitions."""
        if ctx.type == "class_definition":
            self._process_class(ctx, parse_result, parent_symbol, scope_qname, symbols_list, decorators)
        elif ctx.type == "function_definition":
            self._process_function(ctx, parse_result, parent_symbol, scope_qname, symbols_list, decorators)

    def _process_class(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        decorators: Tuple[str, ...] = (),
    ) -> None:
        """Extract Python class symbol."""
        name_node = ctx.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text
        qualified_name = f"{scope_qname}.{name}"
        if any(s.qualified_name == qualified_name for s in symbols_list):
            qualified_name = f"{scope_qname}.{name}_L{ctx.start_line}"

        visibility = self._determine_visibility(name)

        superclasses_node = ctx.child_by_field_name("superclasses")
        bases_str = f"({superclasses_node.text})" if superclasses_node else ""
        signature = f"class {name}{bases_str}"

        body_node = ctx.child_by_field_name("body")
        docstring = self._extract_docstring_from_block(body_node) if body_node else None

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
            signature=signature,
            docstring=docstring,
            decorators=decorators,
            visibility=visibility,
            is_async=False,
            is_exported=True,
        )
        symbols_list.append(class_symbol)

        if body_node:
            self._traverse_node(
                ctx=body_node,
                parse_result=parse_result,
                parent_symbol=class_symbol,
                scope_qname=qualified_name,
                symbols_list=symbols_list,
                decorators=(),
            )

    def _process_function(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
        decorators: Tuple[str, ...] = (),
    ) -> None:
        """Extract Python function/method/constructor symbol."""
        name_node = ctx.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text
        qualified_name = f"{scope_qname}.{name}"
        if any(s.qualified_name == qualified_name for s in symbols_list):
            qualified_name = f"{scope_qname}.{name}_L{ctx.start_line}"

        visibility = self._determine_visibility(name)

        is_async = any(c.type == "async" for c in ctx.node.children) or ctx.text.startswith("async ")

        if parent_symbol.kind == SymbolKind.CLASS:
            if name == "__init__":
                kind = SymbolKind.CONSTRUCTOR
            elif any("@property" in dec for dec in decorators):
                kind = SymbolKind.PROPERTY
            else:
                kind = SymbolKind.METHOD
        else:
            kind = SymbolKind.FUNCTION

        params_node = ctx.child_by_field_name("parameters")
        params_str = params_node.text if params_node else "()"
        return_type_node = ctx.child_by_field_name("return_type")
        ret_str = f" -> {return_type_node.text}" if return_type_node else ""
        async_prefix = "async " if is_async else ""
        signature = f"{async_prefix}def {name}{params_str}{ret_str}"

        body_node = ctx.child_by_field_name("body")
        docstring = self._extract_docstring_from_block(body_node) if body_node else None

        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=file_path,
            qualified_name=qualified_name,
            kind=kind,
        )

        func_symbol = Symbol(
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
            docstring=docstring,
            decorators=decorators,
            visibility=visibility,
            is_async=is_async,
            is_exported=True,
        )
        symbols_list.append(func_symbol)

        if params_node:
            self._extract_parameters(params_node, parse_result, func_symbol, qualified_name, symbols_list)

        if body_node:
            self._traverse_node(
                ctx=body_node,
                parse_result=parse_result,
                parent_symbol=func_symbol,
                scope_qname=qualified_name,
                symbols_list=symbols_list,
                decorators=(),
            )

    def _extract_parameters(
        self,
        params_ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
    ) -> None:
        """Extract parameters from function signature."""
        for param in params_ctx.node.children:
            p_ctx = ASTNodeContext(param, params_ctx.code_bytes)
            if p_ctx.type in (
                "identifier",
                "typed_parameter",
                "default_parameter",
                "typed_default_parameter",
                "list_splat_pattern",
                "dictionary_splat_pattern",
            ):
                param_name = p_ctx.text.split(":")[0].split("=")[0].strip()
                if param_name in ("self", "cls", "(", ")", ","):
                    continue

                param_qname = f"{scope_qname}.{param_name}"
                if any(s.qualified_name == param_qname for s in symbols_list):
                    param_qname = f"{scope_qname}.{param_name}_L{p_ctx.start_line}"

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
                        name=param_name,
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

    def _process_import(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
    ) -> None:
        """Extract import statements."""
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

    def _process_assignment_or_expr(
        self,
        ctx: ASTNodeContext,
        parse_result: ParseResult,
        parent_symbol: Symbol,
        scope_qname: str,
        symbols_list: List[Symbol],
    ) -> None:
        """Extract variable / constant assignments."""
        assign_node = ctx if ctx.type == "assignment" else ctx.find_first_child_of_type("assignment")
        if not assign_node:
            return

        left_node = assign_node.child_by_field_name("left")
        if not left_node or left_node.type != "identifier":
            return

        name = left_node.text
        if not name:
            return

        type_node = assign_node.child_by_field_name("type")
        is_final = type_node is not None and "Final" in type_node.text
        is_uppercase = name.isupper() and len(name) > 1

        kind = SymbolKind.CONSTANT if (is_uppercase or is_final) else SymbolKind.VARIABLE
        qname = f"{scope_qname}.{name}"
        if any(s.qualified_name == qname for s in symbols_list):
            qname = f"{scope_qname}.{name}_L{ctx.start_line}_{ctx.start_column}"

        visibility = self._determine_visibility(name)

        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=file_path,
            qualified_name=qname,
            kind=kind,
        )

        symbols_list.append(
            Symbol(
                id=symbol_id,
                name=name,
                qualified_name=qname,
                kind=kind,
                language=lang,
                file_path=file_path,
                start_line=ctx.start_line,
                end_line=ctx.end_line,
                start_column=ctx.start_column,
                end_column=ctx.end_column,
                parent_symbol=parent_symbol.id,
                signature=assign_node.text,
                docstring=None,
                decorators=(),
                visibility=visibility,
                is_async=False,
                is_exported=True,
            )
        )

    def _extract_docstring_from_block(self, block_ctx: Optional[ASTNodeContext]) -> Optional[str]:
        """Extract leading string docstring from block or body."""
        if not block_ctx:
            return None

        for child in block_ctx.node.children:
            if child.type == "comment":
                continue
            if child.type == "expression_statement":
                expr_ctx = ASTNodeContext(child, block_ctx.code_bytes)
                str_child = expr_ctx.find_first_child_of_type("string")
                if str_child:
                    raw_text = str_child.text.strip()
                    for quote in ('"""', "'''", '"', "'"):
                        if raw_text.startswith(quote) and raw_text.endswith(quote) and len(raw_text) >= 2 * len(quote):
                            return raw_text[len(quote) : -len(quote)].strip()
                    return raw_text
                break
            else:
                break
        return None

    def _determine_visibility(self, name: str) -> str:
        """Determine Python visibility rule."""
        if name.startswith("__") and not name.endswith("__"):
            return "__private"
        elif name.startswith("_") and not name.endswith("_"):
            return "_protected"
        return "public"
