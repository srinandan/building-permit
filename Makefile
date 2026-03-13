.PHONY: all frontend api agent contractor-agent clean

all: frontend api agent contractor-agent

frontend:
	$(MAKE) -C frontend

api:
	$(MAKE) -C api

agent:
	$(MAKE) -C agent

contractor-agent:
	$(MAKE) -C contractor-agent

clean:
	$(MAKE) -C frontend clean
	$(MAKE) -C api clean
	$(MAKE) -C agent clean
	$(MAKE) -C contractor-agent clean
