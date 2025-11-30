from pathlib import Path

from dumps.ghidra import scaffold


def test_build_paths_exist():
    build = scaffold.BuildPaths.from_build(scaffold.DEFAULT_BUILD_ID)
    assert build.missing() == []


def test_tasks_have_scripts():
    for task in scaffold.TASKS.values():
        assert task.script_path().exists(), f"Missing script for task {task.name}"


def test_headless_command_layout():
    build = scaffold.BuildPaths.from_build(scaffold.DEFAULT_BUILD_ID)
    task = scaffold.TASKS["kernel-symbols"]
    fake_headless = "/opt/ghidra/analyzeHeadless"
    cmd, out_dir = scaffold.build_headless_command(task, build, fake_headless)

    assert cmd[0] == fake_headless
    assert "-import" in cmd
    assert str(build.kernel) in cmd
    assert out_dir == scaffold.OUT_ROOT / scaffold.DEFAULT_BUILD_ID / task.name
    scaffold.ensure_under(out_dir, scaffold.OUT_ROOT)


def test_render_shell_command_quotes():
    cmd = ["ghidra", "/tmp path", "proj", "-import", "/foo bar"]
    rendered = scaffold.render_shell_command(cmd)
    assert "'/tmp path'" in rendered
    assert "'/foo bar'" in rendered
