.PHONY: all install frontend api agent contractor-agent assessor-mcp-server stop clean deploy

# Running 'all' will now trigger all targets in the background
all: 
	@$(MAKE) frontend &
	@$(MAKE) api &
	@$(MAKE) agent &
	@$(MAKE) contractor-agent &
	@$(MAKE) assessor-mcp-server &
	@wait # Optional: keeps the parent 'make' alive until all children finish

install:
	$(MAKE) -C frontend install
	$(MAKE) -C api install
	$(MAKE) -C agent install
	$(MAKE) -C contractor-agent install
	$(MAKE) -C assessor-mcp-server install

frontend:
	$(MAKE) -C frontend start

api:
	$(MAKE) -C api start

agent:
	$(MAKE) -C agent start

contractor-agent:
	$(MAKE) -C contractor-agent start

assessor-mcp-server:
	$(MAKE) -C assessor-mcp-server start

deploy:
	$(MAKE) -C frontend deploy
	$(MAKE) -C api deploy
	$(MAKE) -C agent deploy
	$(MAKE) -C contractor-agent deploy
	$(MAKE) -C assessor-mcp-server deploy

stop:
	-pkill -f "make -C frontend"
	-pkill -f "make -C api"
	-pkill -f "make -C agent"
	-pkill -f "make -C contractor-agent"
	-pkill -f "make -C assessor-mcp-server"

clean:
	$(MAKE) -C frontend clean
	$(MAKE) -C api clean
	$(MAKE) -C agent clean
	$(MAKE) -C contractor-agent clean
	$(MAKE) -C assessor-mcp-server clean
