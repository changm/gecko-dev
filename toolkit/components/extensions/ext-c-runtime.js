"use strict";

function runtimeApiFactory(context) {
  let {extension} = context;

  return {
    runtime: {
      onConnect: context.messenger.onConnect("runtime.onConnect"),

      onMessage: context.messenger.onMessage("runtime.onMessage"),

      onConnectExternal: context.messenger.onConnectExternal("runtime.onConnectExternal"),

      onMessageExternal: context.messenger.onMessageExternal("runtime.onMessageExternal"),

      connect: function(extensionId, connectInfo) {
        let name = connectInfo !== null && connectInfo.name || "";
        extensionId = extensionId || extension.id;
        let recipient = {extensionId};

        return context.messenger.connect(context.messageManager, name, recipient);
      },

      sendMessage: function(...args) {
        let options; // eslint-disable-line no-unused-vars
        let extensionId, message, responseCallback;
        if (typeof args[args.length - 1] === "function") {
          responseCallback = args.pop();
        }
        if (!args.length) {
          return Promise.reject({message: "runtime.sendMessage's message argument is missing"});
        } else if (args.length === 1) {
          message = args[0];
        } else if (args.length === 2) {
          if (typeof args[0] === "string" && args[0]) {
            [extensionId, message] = args;
          } else {
            [message, options] = args;
          }
        } else if (args.length === 3) {
          [extensionId, message, options] = args;
        } else if (args.length === 4 && !responseCallback) {
          return Promise.reject({message: "runtime.sendMessage's last argument is not a function"});
        } else {
          return Promise.reject({message: "runtime.sendMessage received too many arguments"});
        }

        if (extensionId != null && typeof extensionId !== "string") {
          return Promise.reject({message: "runtime.sendMessage's extensionId argument is invalid"});
        }

        extensionId = extensionId || extension.id;
        let recipient = {extensionId};

        if (options != null) {
          if (typeof options !== "object") {
            return Promise.reject({message: "runtime.sendMessage's options argument is invalid"});
          }
          if (typeof options.toProxyScript === "boolean") {
            recipient.toProxyScript = options.toProxyScript;
          } else {
            return Promise.reject({message: "runtime.sendMessage's options.toProxyScript argument is invalid"});
          }
        }

        return context.messenger.sendMessage(context.messageManager, message, recipient, responseCallback);
      },

      connectNative(application) {
        let recipient = {
          childId: context.childManager.id,
          toNativeApp: application,
        };

        return context.messenger.connectNative(context.messageManager, "", recipient);
      },

      sendNativeMessage(application, message) {
        let recipient = {
          childId: context.childManager.id,
          toNativeApp: application,
        };
        return context.messenger.sendNativeMessage(context.messageManager, message, recipient);
      },

      get lastError() {
        return context.lastError;
      },

      getManifest() {
        return Cu.cloneInto(extension.manifest, context.cloneScope);
      },

      id: extension.id,

      getURL: function(url) {
        return extension.baseURI.resolve(url);
      },
    },
  };
}

extensions.registerSchemaAPI("runtime", "addon_child", runtimeApiFactory);
extensions.registerSchemaAPI("runtime", "content_child", runtimeApiFactory);
extensions.registerSchemaAPI("runtime", "devtools_child", runtimeApiFactory);
extensions.registerSchemaAPI("runtime", "proxy_script", runtimeApiFactory);
