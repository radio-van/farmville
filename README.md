## Farmville
Python containers management module

### General
This is a simple wrapper around several backends for container management. The idea is to separate container management logic and low-level shell calls to container environment.

### Usage
Inherit your class from `Container` class and add desirable mixins for containers backend (**lxc** backend is available at this moment) and OS-inside-container managent (**alpine** is available at this moment).

### WIP
Module is at the early stage of development. Only basic concept and very basic features are ready yet.
