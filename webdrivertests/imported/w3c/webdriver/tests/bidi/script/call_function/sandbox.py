import pytest

from webdriver.bidi.modules.script import ContextTarget, ScriptEvaluateResultException

from ... import any_int, any_string, recursive_compare
from .. import any_stack_trace


@pytest.mark.asyncio
async def test_sandbox(bidi_session, new_tab):
    # Make changes in window
    await bidi_session.script.call_function(
        function_declaration="() => { window.foo = 1; }",
        target=ContextTarget(new_tab["context"]),
        await_promise=True,
    )

    # Check that changes are not present in sandbox
    result_in_sandbox = await bidi_session.script.call_function(
        function_declaration="() => window.foo",
        target=ContextTarget(new_tab["context"], "sandbox"),
        await_promise=True,
    )
    assert result_in_sandbox == {"type": "undefined"}

    # Make changes in sandbox
    await bidi_session.script.call_function(
        function_declaration="() => { window.bar = 2; }",
        target=ContextTarget(new_tab["context"], "sandbox"),
        await_promise=True,
    )

    # Make sure that changes are present in sandbox
    result_in_sandbox = await bidi_session.script.call_function(
        function_declaration="() => window.bar",
        target=ContextTarget(new_tab["context"], "sandbox"),
        await_promise=True,
    )
    assert result_in_sandbox == {"type": "number", "value": 2}

    # Make sure that changes didn't leak from sandbox
    result_in_window = await bidi_session.script.call_function(
        function_declaration="() => window.bar",
        target=ContextTarget(new_tab["context"]),
        await_promise=True,
    )
    assert result_in_window == {"type": "undefined"}


@pytest.mark.asyncio
async def test_sandbox_with_empty_name(bidi_session, new_tab):
    # BiDi specification doesn't have restrictions of a sandbox name,
    # that's why we want to make sure that it works with an empty name
    await bidi_session.script.call_function(
        function_declaration="() => window.foo = 'bar'",
        target=ContextTarget(new_tab["context"], ""),
        await_promise=True,
    )

    # Make sure that we can find the sandbox with the empty name
    result = await bidi_session.script.call_function(
        function_declaration="() => window.foo",
        target=ContextTarget(new_tab["context"], ""),
        await_promise=True,
    )
    assert result == {"type": "string", "value": "bar"}

    # Make sure that changes didn't leak from sandbox
    result = await bidi_session.script.evaluate(
        expression="window.foo",
        target=ContextTarget(new_tab["context"]),
        await_promise=True,
    )
    assert result == {"type": "undefined"}


@pytest.mark.asyncio
async def test_switch_sandboxes(bidi_session, new_tab):
    # Test that sandboxes are retained when switching between them
    await bidi_session.script.call_function(
        function_declaration="() => { window.foo = 1; }",
        target=ContextTarget(new_tab["context"], "sandbox_1"),
        await_promise=True,
    )
    await bidi_session.script.call_function(
        function_declaration="() => { window.foo = 2; }",
        target=ContextTarget(new_tab["context"], "sandbox_2"),
        await_promise=True,
    )

    result_in_sandbox_1 = await bidi_session.script.call_function(
        function_declaration="() => window.foo",
        target=ContextTarget(new_tab["context"], "sandbox_1"),
        await_promise=True,
    )
    assert result_in_sandbox_1 == {"type": "number", "value": 1}

    result_in_sandbox_2 = await bidi_session.script.call_function(
        function_declaration="() => window.foo",
        target=ContextTarget(new_tab["context"], "sandbox_2"),
        await_promise=True,
    )
    assert result_in_sandbox_2 == {"type": "number", "value": 2}


@pytest.mark.asyncio
async def test_sandbox_with_side_effects(bidi_session, new_tab):
    # Make sure changing the node in sandbox will affect the other sandbox as well
    await bidi_session.script.call_function(
        function_declaration="() => document.querySelector('body').textContent = 'foo'",
        target=ContextTarget(new_tab["context"], "sandbox_1"),
        await_promise=True,
    )
    expected_value = {"type": "string", "value": "foo"}

    result_in_sandbox_1 = await bidi_session.script.call_function(
        function_declaration="() => document.querySelector('body').textContent",
        target=ContextTarget(new_tab["context"], "sandbox_1"),
        await_promise=True,
    )
    assert result_in_sandbox_1 == expected_value

    result_in_sandbox_2 = await bidi_session.script.call_function(
        function_declaration="() => document.querySelector('body').textContent",
        target=ContextTarget(new_tab["context"], "sandbox_2"),
        await_promise=True,
    )
    assert result_in_sandbox_2 == expected_value


@pytest.mark.asyncio
async def test_arguments(bidi_session, new_tab):
    argument = {
        "type": "set",
        "value": [
            {"type": "string", "value": "foobar"},
        ],
    }
    result = await bidi_session.script.call_function(
        function_declaration=f"""(arg) => {{
            if(! (arg instanceof Set))
                throw Error("Argument type should be Set, but was "+
                    Object.prototype.toString.call(arg));
            return arg;
        }}""",
        arguments=[argument],
        await_promise=False,
        target=ContextTarget(new_tab["context"], "sandbox"),
    )

    recursive_compare(argument, result)


@pytest.mark.asyncio
@pytest.mark.parametrize("await_promise", [True, False])
async def test_exception_details(bidi_session, new_tab, await_promise):
    function_declaration = "()=>{{ throw 1 }}"
    if await_promise:
        function_declaration = "async" + function_declaration

    with pytest.raises(ScriptEvaluateResultException) as exception:
        await bidi_session.script.call_function(
            function_declaration=function_declaration,
            await_promise=await_promise,
            target=ContextTarget(new_tab["context"], "sandbox"),
        )

    recursive_compare(
        {
            "realm": any_string,
            "exceptionDetails": {
                "columnNumber": any_int,
                "exception": {"type": "number", "value": 1},
                "lineNumber": any_int,
                "stackTrace": any_stack_trace,
                "text": any_string,
            },
        },
        exception.value.result,
    )
