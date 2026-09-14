#ifndef TEMPLATE_PL_H
#define TEMPLATE_PL_H

#include "template_def.h" // defines win macro, and includes ta_global and our own maketa types
#include <IPlugin>    // Defines the plugin architecture.

// forward or external declarations
class TemplatePlugin;
class TemplatePluginState; //

TypeDef_Of(TemplatePlugin);
TypeDef_Of(TemplatePluginState);


// you can replace these with your own version
// TODO: if you change these values, change them in CMakeLists.txt as well

#define PLUGIN_VERSION_MAJOR @PLUGIN_VERSION_MAJOR@
#define PLUGIN_VERSION_MINOR @PLUGIN_VERSION_MINOR@
#define PLUGIN_VERSION_PATCH @PLUGIN_VERSION_PATCH@

// The TemplatePlugin class allows this to be a plugin. It usually won't
// need to be modified.

class TEMPLATE_API TemplatePlugin : public QObject,
  public IPlugin
{ // #NO_CSS #NO_MEMBERS
  Q_OBJECT
#ifndef __MAKETA__
  Q_PLUGIN_METADATA(IID "@EMERGENT_PLUGIN_UNIQUEID@")
  // Tells Qt which interfaces are implemented by this class
  Q_INTERFACES(IPlugin)
#endif
public:
  static const taVersion	version;
  
  explicit TemplatePlugin(QObject* parent = nullptr);

public: // IPlugin interface
  TYPED_OBJECT(TemplatePlugin)
  const char*	desc() override;
  const char*	name() override {return "Template";}
  const char*	uniqueId() override;
  const char*	url() override;
  
  int		NotifyTacssVersion(const taVersion& tav, bool& is_ok) override {(void)tav; is_ok = true; return 0;}
    // we pass temt version; set is_ok false if this version is no good for plugin
  int		GetVersion(taVersion& tav) override {tav = version; return 0;}
  int 		InitializeTypes() override;
  int 		InitializePlugin() override;
};

// Associates a string with the interface TemplatePlugin
Q_DECLARE_INTERFACE(TemplatePlugin, "emergent.TemplatePlugin/1.0")
   
#endif
