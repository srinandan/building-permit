.PHONY: all frontend api agent contractor-agent assessor-mcp-server clean

# Running 'all' will now trigger all targets in the background
all:
	@$(MAKE) frontend &
	@$(MAKE) api &
	@$(MAKE) agent &
	@$(MAKE) contractor-agent &
	@$(MAKE) assessor-mcp-server &
	@wait # Optional: keeps the parent 'make' alive until all children finish

frontend:
	$(MAKE) -C frontend start

api:
	$(MAKE) -C api start

agent:
	$(MAKE) -C agent start

contractor-agent:
	$(MAKE) -C contractor-agent start

assessor-mcp-server:
	$(MAKE) -C assessor-mcp-server

clean:
	$(MAKE) -C frontend clean
	$(MAKE) -C api clean
	$(MAKE) -C agent clean
	$(MAKE) -C contractor-agent clean
	$(MAKE) -C assessor-mcp-server clean
