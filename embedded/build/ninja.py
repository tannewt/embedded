from embedded import build

async def run(build_dir):
	extra_parallel = 0
	while not build.shared_semaphore.locked():
		extra_parallel += 1
		# Await even though we should get it immediately.
		await build.shared_semaphore.acquire()
	# Release one for run command
	build.shared_semaphore.release()
	extra_parallel -= 1

	try:
		await build.run_command(["ninja", "-j", str(extra_parallel + 1)], working_directory=build_dir)
	finally:
		for i in range(extra_parallel):
			build.shared_semaphore.release()
