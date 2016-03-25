#!/usr/bin/make -f

patternfly = v3.0.0
nod = 2.0.12

all: \
	wifinator/static/vendor/patternfly \
	wifinator/static/vendor/nod.js

src/${patternfly}.tar.gz:
	mkdir -p src
	cd src && curl -sLO https://github.com/patternfly/patternfly/archive/${patternfly}.tar.gz

src/nod.js:
	mkdir -p src
	cd src && curl -sLO https://raw.githubusercontent.com/casperin/nod/${nod}/nod.js

wifinator/static/vendor/patternfly: src/${patternfly}.tar.gz
	rm -rf $@
	mkdir -p $@
	cd src && tar -xf ${patternfly}.tar.gz -C ../$@ --strip-components=2 --mode a-X '*/dist'
	chmod 644 $@/*/*.*

wifinator/static/vendor/nod.js: src/nod.js
	mkdir -p $(dir $@)
	install -m644 $< $@

wifinator/static/vendor/validations.js: src/validations.js
	mkdir -p $(dir $@)
	install -m644 $< $@

clean:
	rm -rf src wifinator/static/vendor

# EOF
