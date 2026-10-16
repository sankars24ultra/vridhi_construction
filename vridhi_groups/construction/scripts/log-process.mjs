import { spawn } from 'node:child_process'
import { appendFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const [component, command, ...args] = process.argv.slice(2)
if (!['backend-server', 'frontend-server'].includes(component) || !command) {
  throw new Error('Usage: node scripts/log-process.mjs backend-server|frontend-server command [args]')
}
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const child = spawn(command, args, { stdio: ['inherit', 'pipe', 'pipe'], shell: process.platform === 'win32' })
function record(stream, chunk) {
  const directory = resolve(root, 'data', 'logs', new Date().toISOString().slice(0, 10))
  mkdirSync(directory, { recursive: true })
  appendFileSync(resolve(directory, `${component}.log`), chunk)
  stream.write(chunk)
}
child.stdout.on('data', chunk => record(process.stdout, chunk))
child.stderr.on('data', chunk => record(process.stderr, chunk))
child.on('error', error => { record(process.stderr, `${error.message}\n`); process.exitCode = 1 })
child.on('exit', code => { process.exitCode = code ?? 1 })
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal))