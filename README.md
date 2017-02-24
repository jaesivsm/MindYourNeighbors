# MindYourNeighbors

Launching scripts depending on you direct neighbors

## How ?

*MindYourNeighbors* basically parse the ip-neighbor and, if results are found that are not excluded by the configuration, a configured command will be launched once.

## Why ?

The original use case :

A linux box used as a router as well as a home server. On this box runs several pieces of software which can be very bandwith consuming (ie: transmission).
I wanted to shut down this software when other users were using the network.

## Features

*MindYourNeighbors* behavior's can be controlled through configuration file placed either in `~/.config/mind_your_neighbords.conf` or in `/etc/mind_your_neighbords.conf`.

The configuration file is organized in sections. The **DEFAULT** section holds the default options which will be inherited by all the other sections (except for the logging level and the cache file path). All the other section will be read one by one ; each time the condition defined in `filter_on_regex` or `filter_on_machine` is matched and isn't excluded by those defined in neither `exclude`, `filter_out_regex` or `filter_out_machine` the cache will be filled with either a marker `neighbor` or a marker `no neighbor`.

Cache length can't exceed the `threshold`, as only the **REACHABLE** lines in the result of the `ip neigh` command are taken in account and as those lines vary quite a bit, the threshold parameter allows you to configure how quickly a change of state can occure.

When the cache is filled the only `neighbor` or `no neighbor` markers, the corresponding command is executed once.

##### Known Machines

You can fill a section with `known_machine` as title in which you'll write the name and mac address of machine you're aware of. You'll then be able to filter them out or in through `filter_out_machine` and `filter_on_machine`.

Please refer to the configuration example file for practical use cases.

## Options list

#### Default section options

 * `loglevel`: allows you to choose the verbosity level in the syslog between `DEBUG`, `INFO`, `WARN`, `ERROR` and `FATAL`.
 * `cache_file`: the path to the file where *MindYourNeighbors* will store its cache.

#### By sections, overridable options

 * `threshold`: the number of consecutive matches (or un matches) it takes for *MindYourNeighbors* to execute the "match" or "no match" command.
 * `filter_on_regex`: a regex to filters lines from the `ip neigh` command, lines will have to match to be counted
 * `filter_out_regex`: a regex to filters lines from the `ip neigh` command, matching line will be excluded
 * `exclude`: a comma separated list of string. If one of those string should be found in a `ip neigh` line, it should be excluded.
 * `filter_on_machine`: a comma separated list of machine names to filter in (they must be registered in `known_machine`)
 * `filter_out_machine`: a comma separated list of machine names to filter out (they must be registered in `known_machine`)
 * `command_match`: A command to execute when the cache has been filed with `neighbor` marker.
 * `command_no_match`: A command to execute when the cache has been filed with `no neighbor` marker.
 * `device`: if none provide the `ip neigh` command will be parsed else `ip neigh show dev <device>`.
 * `enable`: a boolean (`true` or `false`), enabling or disabling a section.
 * `nslookup`: a boolean (`true` or `false`), making *MindYourNeighbors* looking up domain names for IP it'll print in the logs. Can be useful for debuging.
 * `error_on_stderr`: a boolean (`true` or `false`); if `true` and the command print something on *stderr*, the command will be ignored and executed again.
 * `cron`: a cron styled time description in which the section will be activated
