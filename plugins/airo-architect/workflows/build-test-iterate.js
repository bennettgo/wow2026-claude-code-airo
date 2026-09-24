export const meta = {
  name: 'airo-build-test-iterate',
  description: 'Author tests, then build + test + iterate a Workato solution from plan.json',
  phases: [{ title: 'Author tests' }, { title: 'Build, test, iterate' }],
}

const { slug, target, sandbox_folder, max_iterations = 3 } = args

phase('Author tests')
const tests = await agent(
  `Read builds/${slug}/requirements.md and builds/${slug}/plan.json. Generate sample test cases.`,
  { agentType: 'test-author', model: 'haiku',
    schema: { type: 'object', required: ['tests'], properties: { tests: { type: 'array' } } } }
)

phase('Build, test, iterate')
const result = await agent(
  `Build the plan for slug="${slug}", target="${target}" in sandbox folder "${sandbox_folder}".\n` +
  `plan: builds/${slug}/plan.json\ntests: ${JSON.stringify(tests.tests)}\n` +
  `Provision in the sandbox only, run the tests, grade, and iterate up to ${max_iterations} times. ` +
  `Write builds/${slug}/build-state.json. Return {status, build_state, results, changes_made}.`,
  { agentType: 'builder-integrator', model: 'sonnet',
    schema: { type: 'object', required: ['status', 'results'],
      properties: { status: { enum: ['passed', 'stuck'] }, results: { type: 'array' },
                    build_state: { type: 'object' }, changes_made: { type: 'array' } } } }
)

return { tests: tests.tests, ...result }
