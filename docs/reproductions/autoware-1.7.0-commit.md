# Locate the personal commit based on Autoware 1.7.0

Recorded on **2026-10-22**, using the user's timezone, **Asia/Ho_Chi_Minh**.
This record is for someone locating the personal script commit in the top-level
Autoware repository, rather than in the separate Universe repository.

## Scope and historical snapshot

The lookup identified commit
`b8d4a5b90b5e3ab4f1b805158f2005ac2bd44d06` in
`/workspace/vule/autoware`. Its subject is:

```text
feat: add Green Traffic Light Publisher and Docker launcher scripts
```

Its parent is `cc19bae1fb32c72b2a20416e95f5707e457ab547`, the commit
checked out at tag `1.7.0` during this investigation.

The results below describe the original lookup, **before** the later creation of
the local `saved-autoware-edits` branch. That later operation and any push are
outside this document's scope. Repeating these commands shows the state at the
time of the repeat; branch and reflog output can therefore differ.

## Prerequisites, environment, and inputs

- A Linux host with a shell and Git installed. The Git executable version was
  not recorded during the original lookup.
- The existing repository at `/workspace/vule/autoware`, including its local
  `.git` history, objects, and reflog. A fresh upstream clone alone will not
  contain this personal commit or this machine's reflog.
- Read permission for the repository and its Git metadata. The recorded checks
  succeeded; Git reported no ownership or permission errors.
- No Conda environment activation, Docker container, ROS environment, Python
  packages, GPU, dataset, or external service is required.
- No credentials or network access are required. Remote-tracking references
  are inspected locally; they are not refreshed from GitHub.
- Input commit: `b8d4a5b90b5e3ab4f1b805158f2005ac2bd44d06`.
- Reference release: Autoware `1.7.0`.
- No parameter files, thresholds, seeds, or environment-variable overrides are
  used. The commands do not change Git configuration or the working tree.

The commands use `git -C`, so they work from a fresh shell in any working
directory. If the repository has moved, replace `/workspace/vule/autoware` in
each command with its new absolute path.

## Runnable commands

Run each command separately so that its output and exit status can be associated
with the question being checked.

### 1. Check the current checkout and working files

```bash
git -C /workspace/vule/autoware status --short --branch
```

This reports whether the checkout is on a branch and lists uncommitted or
untracked files. The original command exited `0` and printed:

```text
## HEAD (no branch)
```

There were no file-status lines, so the working tree was clean at that point.

### 2. Identify the detached tag and local branch pointers

```bash
git -C /workspace/vule/autoware branch -vv
```

This lists local branches and their tip commits. The command exited `0`. The
relevant recorded lines were:

```text
* (HEAD detached at 1.7.0) cc19bae chore: update nebula to v0.3.2.2 (#6820)
  main 5b09eed [upstream/main: behind 91] feat(docker): bake runtime deps into devel images (#7104)
```

The command output was condensed by the terminal tooling; the lines above are
the relevant excerpt, not a complete inventory of all references.

### 3. Inspect the history of the current checkout

```bash
git -C /workspace/vule/autoware log -5 --oneline --decorate
```

The limit is the five most recent commits reachable from the current `HEAD`.
The command exited `0` and printed:

```text
cc19bae (HEAD, tag: 1.7.0) chore: update nebula to v0.3.2.2 (#6820)
73ee57b feat(autoware_path_optimizer): meta-repository changes for acados (#6771)
8738544 feat: remove tier4_ad_api_adaptor (#6782)
5fa4b54 feat: update autoware.repos file for verison 1.7.0 (#6812)
9ea2bdd chore(ansible): update centerpoint model configs (#6815)
```

The personal commit was not in this five-commit view of `HEAD`.

### 4. Find the personal commit in checkout history

```bash
git -C /workspace/vule/autoware reflog -12 --oneline
```

This examines up to twelve local `HEAD` movements, including commits that are
no longer reachable from the current checkout. The command exited `0`. The
recorded output was:

```text
cc19bae HEAD@{0}: checkout: moving from main to 1.7.0
5b09eed HEAD@{1}: checkout: moving from b8d4a5b90b5e3ab4f1b805158f2005ac2bd44d06 to main
b8d4a5b HEAD@{2}: commit: feat: add Green Traffic Light Publisher and Docker launcher scripts
cc19bae HEAD@{3}: checkout: moving from 10718787ba6e28f038a0cb29ff99cc627b5abfd2 to 1.7.0
1071878 HEAD@{4}: checkout: moving from cc19bae1fb32c72b2a20416e95f5707e457ab547 to 1.9.0
cc19bae HEAD@{5}: checkout: moving from 10718787ba6e28f038a0cb29ff99cc627b5abfd2 to 1.7.0
1071878 HEAD@{6}: checkout: moving from cc19bae1fb32c72b2a20416e95f5707e457ab547 to 1.9.0
cc19bae HEAD@{7}: checkout: moving from main to tags/1.7.0
5b09eed HEAD@{8}: clone: from https://github.com/autowarefoundation/autoware.git
```

`HEAD@{2}` was the matching entry during the original lookup. Reflog positions
change as new operations are performed; use the full commit ID below for a
stable lookup while the object remains available.

### 5. Verify the commit, parent, and changed files

```bash
git -C /workspace/vule/autoware show --stat --format='%H%n%P%n%s' b8d4a5b90b5e3ab4f1b805158f2005ac2bd44d06
```

This prints the full commit ID, parent ID, subject, and file-change statistics.
The command exited `0` and printed:

```text
b8d4a5b90b5e3ab4f1b805158f2005ac2bd44d06
cc19bae1fb32c72b2a20416e95f5707e457ab547
feat: add Green Traffic Light Publisher and Docker launcher scripts

 green_traffic_light_publisher.py | 383 +++++++++++++++++++++++++++++++++++++++
 run_in_docker.sh                 | 163 +++++++++++++++++
 tm_no_tailgailing.py             |  81 +++++++++
 3 files changed, 627 insertions(+)
```

The parent matches the `1.7.0` checkout observed in step 3. The statistics count
inserted lines; they do not measure whether the scripts work correctly.

### 6. Check whether a named reference contains the commit

```bash
git -C /workspace/vule/autoware for-each-ref \
  --contains=b8d4a5b90b5e3ab4f1b805158f2005ac2bd44d06 \
  --format='%(refname:short)' refs/heads refs/remotes refs/tags
```

This searches local branches, locally stored remote-tracking branches, and tags
for references whose history includes the commit. The command exited `0` with
**empty stdout** during the original lookup. That successful empty result meant
none of those local references contained it at that time. It is distinct from
a command failure or a missing commit object.

## Outputs and interpretation

All six lookup commands produced terminal output or a successful empty result.
No standalone output logs or diagnostic scripts were created. The captured
results are embedded above in this document, whose output location is
`docs/reproductions/autoware-1.7.0-commit.md`.

The lookup established that the personal three-script commit existed in the
**top-level** repository and was based directly on the commit tagged `1.7.0`.
The checkout was at the parent release commit, so those additions were not
part of the checked-out files at that moment. The reflog retained the personal
commit even though no checked local branch, remote-tracking branch, or tag
contained it.

The similarly discussed commit
`b384b38589b2dff228bc4db54f5d67cb735d72d6` belongs to the separate
`src/universe/autoware_universe` Git repository. It is not the personal
top-level script commit identified here.

## Success, failures, and limitations

- All six recorded top-level lookup commands completed with exit status `0`.
  This was a Git-history inspection, not a software test run.
- A matching full ID, parent, subject, and three-file summary in step 5 identify
  the intended commit. A missing or invalid object error means the local clone
  no longer has the input object, or the command is running against a different
  repository. That is not a successful reproduction of the lookup.
- Reflogs are local and can expire. A copied or fresh clone may lack the
  original reflog even if it contains the commit through another reference.
- Branch pointers, working files, and reflog positions are historical snapshots.
  In particular, the later `saved-autoware-edits` branch preparation can make
  step 6 return that branch instead of the original empty result.
- Inspecting remote-tracking references without contacting GitHub does not
  establish whether a commit exists anywhere on the remote service.
- These commands did not restore files, create branches, push commits, rebuild
  Autoware, run CARLA or ROS nodes, or test any of the scripts. Those operations
  and their outcomes are outside the approved lookup record.
