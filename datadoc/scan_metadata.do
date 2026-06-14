* ============================================================
* SCAN METADATA - Extract variable metadata from all .dta files
* ============================================================
*
* Output: CSV with one row per variable per file.
*         Contains no microdata - safe to take out of secure zone.
*
* Program location: H:\metadata_scan\scan_metadata.do
* ============================================================

clear all
set more off

global scandir "W:\1191"
global scanout "H:\metadata_scan\metadata_scan.csv"

di _n "============================================"
di    "METADATA SCAN"
di    "Root:   $scandir"
di    "Output: $scanout"
di    "============================================"

* Write CSV header
tempname fh
file open `fh' using "$scanout", write replace
file write `fh' "filepath,filename,nobs,nvar,varname,vartype,format,varlabel" _n
file close `fh'

* ----------------------------------------------------------
* Step 1: Build directory list into a dataset
* ----------------------------------------------------------
clear
set obs 1
gen str260 dirpath = "$scandir"

* Expand 3 levels deep
forvalues level = 1/3 {
	local curN = _N
	forvalues i = 1/`curN' {
		local thisdir = dirpath[`i']
		capture local subdirs : dir "`thisdir'" dirs "*", respectcase
		if _rc == 0 {
			foreach sd of local subdirs {
				local newN = _N + 1
				set obs `newN'
				replace dirpath = "`thisdir'/`sd'" in `newN'
			}
		}
	}
}

local totalN = _N
di _n "Found `totalN' directories to scan"

* Save to a text file (one path per line) to avoid quoting issues
tempfile dirlist_file
file open `fh' using "`dirlist_file'", write replace
forvalues i = 1/`totalN' {
	local p = dirpath[`i']
	file write `fh' `"`p'"' _n
}
file close `fh'

* ----------------------------------------------------------
* Step 2: Scan each directory
* ----------------------------------------------------------
local totalfiles = 0

file open `fh' using "`dirlist_file'", read
file read `fh' thisdir

while r(eof) == 0 {

	capture local files : dir "`thisdir'" files "*.dta", respectcase

	if _rc == 0 {
		local nf = 0
		foreach f of local files {
			local nf = `nf' + 1
			local fullpath "`thisdir'/`f'"

			local descok = 1
			capture {
				qui describe using "`fullpath'"
				local nobs = r(N)
				local nvar = r(k)
			}
			if _rc != 0 local descok = 0

			local useok = 0
			if `descok' == 1 {
				capture use "`fullpath'" in 1, clear
				if _rc == 0 local useok = 1
			}

			if `useok' == 1 {
				tempname fh2
				file open `fh2' using "$scanout", write append
				qui ds
				local allvars `r(varlist)'
				foreach v of local allvars {
					local vtype ""
					local vfmt ""
					local vlab ""
					capture local vtype : type `v'
					capture local vfmt  : format `v'
					capture local vlab  : variable label `v'
					* Clean label: replace problematic characters
					capture local vlab = subinstr(`"`vlab'"', `"""', "'", .)
					capture local vlab = subinstr(`"`vlab'"', ",", ";", .)
					capture local vlab = subinstr(`"`vlab'"', char(230), "ae", .)
					capture local vlab = subinstr(`"`vlab'"', char(248), "oe", .)
					capture local vlab = subinstr(`"`vlab'"', char(229), "aa", .)
					capture local vlab = subinstr(`"`vlab'"', char(198), "AE", .)
					capture local vlab = subinstr(`"`vlab'"', char(216), "OE", .)
					capture local vlab = subinstr(`"`vlab'"', char(197), "AA", .)
					* Try to write; if it still fails, write without label
					capture file write `fh2' `""`fullpath'","`f'",`nobs',`nvar',"`v'","`vtype'","`vfmt'","`vlab'""' _n
					if _rc != 0 {
						capture file write `fh2' "`fullpath',`f',`nobs',`nvar',`v',`vtype',`vfmt',(encoding)" _n
					}
				}
				file close `fh2'
			}
		}
		if `nf' > 0 {
			local totalfiles = `totalfiles' + `nf'
			di "  `thisdir' - `nf' files"
		}
	}

	file read `fh' thisdir
}
file close `fh'

di _n "============================================"
di    "SCAN COMPLETE"
di    "Scanned `totalN' directories"
di    "Found `totalfiles' .dta files"
di    "Output: $scanout"
di    "============================================"

global scandir ""
global scanout ""
