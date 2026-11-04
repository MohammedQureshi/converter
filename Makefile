# Common tasks. Everything runs in Docker, including the supply-chain tools.

IMAGE ?= pdfa-converter:runtime
PLATFORM ?=
SYFT_IMAGE ?= anchore/syft:v1.56.0@sha256:697ae864af1299cfa43c54b161cea3dd65c6d54de82e3dba66ea3dccb3acc313
TRIVY_IMAGE ?= aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c
# Set to 1 to make `make scan` fail when findings exist, for example in CI.
TRIVY_EXIT_CODE ?= 0
TRIVY_SEVERITY ?= HIGH,CRITICAL
BUILD_ARGS ?=

.PHONY: help build test test-offline load up down licenses image-tar sbom scan clean

help:
	@echo "build         Build the production image ($(IMAGE))"
	@echo "test          Build and run the full test suite on the internal-only network"
	@echo "test-offline  Run the tests with all networking disabled"
	@echo "load          Run the load test and print latency tables"
	@echo "up, down      Start or stop the service on port 8080"
	@echo "licenses      Copy THIRD_PARTY_LICENSES.md out of the production image"
	@echo "sbom          Generate SPDX and CycloneDX SBOMs with syft, in sbom/"
	@echo "scan          Scan the production image with trivy"

build:
	docker build $(BUILD_ARGS) --target runtime -t $(IMAGE) .

test:
	docker compose -f docker-compose.test.yml run --rm --build converter pytest

test-offline:
	docker build $(BUILD_ARGS) --target test -t pdfa-converter:test .
	docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
		--tmpfs /tmp:size=2g,mode=1777,uid=10001,gid=10001,exec \
		pdfa-converter:test pytest -m "not load"

load:
	docker compose -f docker-compose.test.yml run --rm --build converter pytest tests/test_load.py -s

up:
	docker compose up -d --build

down:
	docker compose down --remove-orphans

licenses: build
	docker run --rm --entrypoint cat $(IMAGE) /srv/THIRD_PARTY_LICENSES.md > THIRD_PARTY_LICENSES.md

# The image is exported to a file, so neither tool needs the Docker socket.
image-tar: build
	mkdir -p sbom
	docker save $(IMAGE) -o sbom/image.tar

sbom: image-tar
	docker run --rm -v "$(CURDIR)/sbom:/sbom" $(SYFT_IMAGE) docker-archive:/sbom/image.tar \
		-o spdx-json=/sbom/pdfa-converter.spdx.json \
		-o cyclonedx-json=/sbom/pdfa-converter.cdx.json
	rm -f sbom/image.tar

scan: image-tar
	docker run --rm -v "$(CURDIR)/sbom:/sbom" -v pdfa-converter-trivy-cache:/root/.cache/trivy $(TRIVY_IMAGE) \
		image --input /sbom/image.tar --scanners vuln --severity $(TRIVY_SEVERITY) \
		--ignore-unfixed --exit-code $(TRIVY_EXIT_CODE)
	rm -f sbom/image.tar

clean:
	rm -f sbom/image.tar
